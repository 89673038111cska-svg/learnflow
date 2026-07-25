"""Learning mechanics service.

Core rules (from spec):
- Card is mastered when EVERY exercise type for it is passed:
  3 consecutive correct answers, first attempt, no hints, in different sessions.
- Mastered cards go to spaced repetition: 1d → 3d → 7d → 14d → 30d.
- Failed review returns card to learning (progress partially reset).
- Next card in a topic unlocks only after current is mastered.
"""
from datetime import datetime, timedelta
from typing import Optional

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
    return " ".join(answer.strip().lower().split())


def check_answer(card: Card, exercise_type: str, answer: str) -> bool:
    """Deterministic answer check (no LLM)."""
    expected = card.back_content
    # For complex types back_content may be JSON — for MVP compare normalized text
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

    # "Different session" check: last attempt must be from another session
    different_session = (
        progress.last_session_id is None
        or progress.last_session_id != session.id
    )

    if correct and not used_hint and different_session:
        progress.consecutive_correct += 1
    else:
        # Any failure resets the streak; hint use doesn't count but doesn't reset hard
        if not correct:
            progress.consecutive_correct = 0
        # Hint used: don't increment, don't reset (soft)

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
            # Unlock next card in topic
            await _unlock_next_card(db, card)

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


async def _unlock_next_card(db: AsyncSession, card: Card) -> None:
    """Moves next draft card in topic to learning status."""
    result = await db.execute(
        select(Card)
        .where(Card.topic_id == card.topic_id)
        .where(Card.status == CardStatus.DRAFT)
        .where(Card.order_index > card.order_index)
        .order_by(Card.order_index)
        .limit(1)
    )
    next_card = result.scalar_one_or_none()
    if next_card:
        next_card.status = CardStatus.LEARNING


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
