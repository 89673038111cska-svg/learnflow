"""Learning mechanics service.

Core rules (from spec):
- Card is mastered when EVERY exercise type for it is passed:
  3 consecutive correct answers, first attempt, no hints, in different sessions.
- Mastered cards go to spaced repetition: 1d → 3d → 7d → 14d → 30d.
- Failed review returns card to learning (progress partially reset).
- Next card in a topic unlocks only after current is mastered.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Card, CardProgress, CardStatus, CardType, Review, LearningSession, Topic
)

# Exercise types per card type
EXERCISES_BY_TYPE = {
    CardType.TERM: ["multiple_choice", "reverse_choice", "text_input"],
    CardType.COMMAND: ["fill_blank", "write_command", "find_bug"],
    CardType.PROCEDURE: ["order_steps", "next_step"],
}

REQUIRED_CONSECUTIVE = 3
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 90]  # days
# Min gap between sessions for answers to count as "different sessions"
SESSION_GAP_MINUTES = 30


def get_exercises_for_card(card: Card) -> list[str]:
    return EXERCISES_BY_TYPE.get(card.type, [])


async def get_or_create_session(db: AsyncSession, user_id: int) -> LearningSession:
    """Returns active session or creates new one if last was closed/expired."""
    result = await db.execute(
        select(LearningSession)
        .where(LearningSession.user_id == user_id)
        .where(LearningSession.ended_at.is_(None))
        .order_by(LearningSession.started_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if session is None:
        session = LearningSession(user_id=user_id)
        db.add(session)
        await db.flush()
    elif session.started_at < datetime.utcnow() - timedelta(hours=4):
        # Session too old — close and start new
        session.ended_at = datetime.utcnow()
        session = LearningSession(user_id=user_id)
        db.add(session)
        await db.flush()

    return session


async def get_current_card(db: AsyncSession, topic_id: int) -> Optional[Card]:
    """Returns the card currently being learned in topic (first non-mastered)."""
    result = await db.execute(
        select(Card)
        .where(Card.topic_id == topic_id)
        .where(Card.status == CardStatus.LEARNING)
        .order_by(Card.order_index)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_next_exercise(db: AsyncSession, card: Card) -> Optional[str]:
    """Returns next exercise type to practice for card, or None if all mastered."""
    exercises = get_exercises_for_card(card)
    result = await db.execute(
        select(CardProgress).where(CardProgress.card_id == card.id)
    )
    progress_by_type = {p.exercise_type: p for p in result.scalars().all()}

    for ex_type in exercises:
        p = progress_by_type.get(ex_type)
        if p is None or p.consecutive_correct < REQUIRED_CONSECUTIVE:
            return ex_type
    return None


def normalize_answer(answer: str) -> str:
    """Normalization for deterministic text comparison."""
    return " ".join(str(answer).strip().lower().split())


def get_steps(card: Card) -> list[str]:
    """Шаги процедуры: JSON {"steps": [...]} или многострочный текст."""
    import json

    try:
        data = json.loads(card.back_content)
        if isinstance(data, dict) and isinstance(data.get("steps"), list):
            return [str(s) for s in data["steps"]]
    except (ValueError, TypeError):
        pass
    return [line.strip() for line in card.back_content.splitlines() if line.strip()]


def get_blank_answer(card: Card) -> str:
    """fill_blank: детерминированно скрываем последний токен команды."""
    tokens = card.back_content.split()
    return tokens[-1] if tokens else ""


def get_fill_blank_template(card: Card) -> str:
    tokens = card.back_content.split()
    if len(tokens) < 2:
        return "{{blank}}"
    return " ".join(tokens[:-1]) + " {{blank}}"


def get_expected_answer(card: Card, exercise_type: str) -> Any:
    """Правильный ответ для типа упражнения (детерминированно)."""
    if exercise_type == "reverse_choice":
        return card.front_content
    if exercise_type == "fill_blank":
        return get_blank_answer(card)
    if exercise_type == "order_steps":
        return get_steps(card)
    if exercise_type == "next_step":
        steps = get_steps(card)
        return steps[-1] if steps else ""
    # multiple_choice, text_input, write_command, find_bug
    return card.back_content


def check_answer(card: Card, exercise_type: str, answer: Any) -> bool:
    """Deterministic answer check (no LLM)."""
    expected = get_expected_answer(card, exercise_type)
    if isinstance(expected, list):
        if not isinstance(answer, list):
            return False
        return [normalize_answer(a) for a in answer] == [
            normalize_answer(e) for e in expected
        ]
    return normalize_answer(answer) == normalize_answer(expected)


async def record_attempt(
    db: AsyncSession,
    card: Card,
    exercise_type: str,
    correct: bool,
    used_hint: bool,
    session: LearningSession,
) -> dict:
    """Records attempt and updates progress per mastery rules."""
    result = await db.execute(
        select(CardProgress)
        .where(CardProgress.card_id == card.id)
        .where(CardProgress.exercise_type == exercise_type)
    )
    progress = result.scalar_one_or_none()

    if progress is None:
        progress = CardProgress(card_id=card.id, exercise_type=exercise_type)
        db.add(progress)
        await db.flush()

    now = datetime.utcnow()

    if correct and not used_hint:
        progress.consecutive_correct += 1
    elif used_hint or not correct:
        # Подсказка или ошибка сбрасывают серию (строго по спеке)
        progress.consecutive_correct = 0

    progress.last_attempt_at = now
    progress.last_session_id = session.id

    exercise_mastered = progress.consecutive_correct >= REQUIRED_CONSECUTIVE
    if exercise_mastered and progress.mastered_at is None:
        progress.mastered_at = now

    # Check if whole card is mastered
    card_mastered = False
    if exercise_mastered:
        next_ex = await get_next_exercise(db, card)
        card_mastered = next_ex is None
        if card_mastered and card.status != CardStatus.MASTERED:
            card.status = CardStatus.MASTERED
            await _schedule_first_review(db, card)
            # Следующая карточка откроется сама: get_current_card берёт
            # первую LEARNING по order_index. Черновики (DRAFT) в обучение
            # не поднимаем — только через approve (спека).

    await db.commit()

    return {
        "correct": correct,
        "consecutive_correct": progress.consecutive_correct,
        "required_consecutive": REQUIRED_CONSECUTIVE,
        "exercise_mastered": exercise_mastered,
        "card_mastered": card_mastered,
    }


async def _schedule_first_review(db: AsyncSession, card: Card) -> None:
    review = Review(
        card_id=card.id,
        scheduled_at=datetime.utcnow() + timedelta(days=REVIEW_INTERVALS[0]),
        interval_days=REVIEW_INTERVALS[0],
    )
    db.add(review)


async def generate_exercise(db: AsyncSession, card: Card, exercise_type: str) -> dict:
    """Генерация упражнения (payload зависит от типа). Детерминированная проверка — в check_answer."""
    import random

    rng = random.Random(f"{card.id}:{exercise_type}")

    if exercise_type == "multiple_choice":
        distractors = await _distractors(db, card, field="back")
        options = distractors + [card.back_content]
        rng.shuffle(options)
        return {"kind": exercise_type, "payload": {"prompt": card.front_content, "options": options}}

    if exercise_type == "reverse_choice":
        distractors = await _distractors(db, card, field="front")
        options = distractors + [card.front_content]
        rng.shuffle(options)
        return {"kind": exercise_type, "payload": {"prompt": card.back_content, "options": options}}

    if exercise_type == "text_input":
        return {"kind": exercise_type, "payload": {"prompt": card.front_content}}

    if exercise_type == "fill_blank":
        return {
            "kind": exercise_type,
            "payload": {
                "prompt": card.front_content,
                "template": get_fill_blank_template(card),
            },
        }

    if exercise_type == "write_command":
        return {"kind": exercise_type, "payload": {"prompt": card.front_content}}

    if exercise_type == "find_bug":
        return {
            "kind": exercise_type,
            "payload": {
                "prompt": f"Найди и исправь ошибку: {card.front_content}",
            },
        }

    if exercise_type == "order_steps":
        steps = get_steps(card)
        shuffled = steps[:]
        rng.shuffle(shuffled)
        return {"kind": exercise_type, "payload": {"prompt": card.front_content, "shuffled_steps": shuffled}}

    if exercise_type == "next_step":
        steps = get_steps(card)
        return {
            "kind": exercise_type,
            "payload": {"prompt": card.front_content, "given_steps": steps[:-1]},
        }

    return {"kind": exercise_type, "payload": {"prompt": card.front_content}}


async def _distractors(db: AsyncSession, card: Card, field: str, count: int = 3) -> list[str]:
    """Неправильные варианты из других карточек темы."""
    col = Card.back_content if field == "back" else Card.front_content
    correct = card.back_content if field == "back" else card.front_content
    rows = (
        await db.scalars(
            select(col)
            .where(Card.topic_id == card.topic_id, Card.id != card.id)
        )
    ).all()
    options = [v for v in dict.fromkeys(rows) if normalize_answer(v) != normalize_answer(correct)]
    return options[:count]


async def get_due_reviews(db: AsyncSession, user_id: int) -> list[Card]:
    result = await db.execute(
        select(Card)
        .join(Review, Review.card_id == Card.id)
        .join(Topic, Topic.id == Card.topic_id)
        .where(Topic.user_id == user_id)
        .where(Review.completed_at.is_(None))
        .where(Review.scheduled_at <= datetime.utcnow())
    )
    return list(result.scalars().all())


async def complete_review(db: AsyncSession, card: Card, success: bool) -> None:
    """Completes review: schedules next or returns card to learning on failure."""
    result = await db.execute(
        select(Review)
        .where(Review.card_id == card.id)
        .where(Review.completed_at.is_(None))
        .order_by(Review.scheduled_at.desc())
        .limit(1)
    )
    review = result.scalar_one_or_none()
    if review is None:
        return

    review.completed_at = datetime.utcnow()
    review.success = success

    if success:
        # Next interval
        try:
            idx = REVIEW_INTERVALS.index(review.interval_days)
            next_interval = REVIEW_INTERVALS[min(idx + 1, len(REVIEW_INTERVALS) - 1)]
        except ValueError:
            next_interval = REVIEW_INTERVALS[0]
        next_review = Review(
            card_id=card.id,
            scheduled_at=datetime.utcnow() + timedelta(days=next_interval),
            interval_days=next_interval,
        )
        db.add(next_review)
    else:
        # Failed — card back to learning, partial progress reset
        card.status = CardStatus.LEARNING
        result = await db.execute(
            select(CardProgress).where(CardProgress.card_id == card.id)
        )
        for p in result.scalars().all():
            p.consecutive_correct = max(0, p.consecutive_correct - 1)
            p.mastered_at = None

    await db.commit()
