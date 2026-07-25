"""Механика обучения (issue #6): state + attempt."""
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.models import Card, CardStatus, Review, Topic, User
from app.schemas.schemas import (
    AttemptResult,
    CardResponse,
    ErrorResponse,
    Exercise,
    ExerciseAttempt,
    LearningStateResponse,
)
from app.services import learning as svc

router = APIRouter()

TOPIC_NOT_FOUND = AppError(404, "topic_not_found", "Topic not found")
CARD_NOT_FOUND = AppError(404, "card_not_found", "Card not found")
CARD_NOT_LEARNING = AppError(409, "card_not_learning", "Card is not in learning status")
WRONG_EXERCISE = AppError(
    409, "wrong_exercise", "Exercise kind does not match current next exercise for card"
)

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


async def _reviews_due_count(db: AsyncSession, user_id: int) -> int:
    return await db.scalar(
        select(func.count(Review.id))
        .join(Card, Review.card_id == Card.id)
        .join(Topic, Topic.id == Card.topic_id)
        .where(
            Topic.user_id == user_id,
            Review.completed_at.is_(None),
            Review.scheduled_at <= func.now(),
        )
    ) or 0


@router.get("/state", response_model=LearningStateResponse, responses=ERROR_RESPONSES)
async def get_learning_state(
    topic_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Текущая карточка темы + упражнение + reviews_due + прогресс."""
    topic = await db.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        raise TOPIC_NOT_FOUND

    total = await db.scalar(
        select(func.count(Card.id)).where(
            Card.topic_id == topic_id, Card.status != CardStatus.DRAFT
        )
    ) or 0
    mastered = await db.scalar(
        select(func.count(Card.id)).where(
            Card.topic_id == topic_id, Card.status == CardStatus.MASTERED
        )
    ) or 0

    card = await svc.get_current_card(db, topic_id)
    exercise: Exercise | None = None
    if card is not None:
        next_kind = await svc.get_next_exercise(db, card)
        if next_kind is not None:
            exercise = Exercise(**await svc.generate_exercise(db, card, next_kind))

    return LearningStateResponse(
        topic_id=topic_id,
        current_card=CardResponse.model_validate(card) if card else None,
        exercise=exercise,
        reviews_due=await _reviews_due_count(db, current_user.id),
        cards_total=total,
        cards_mastered=mastered,
        progress_percent=round(100.0 * mastered / total, 1) if total else 0.0,
    )


@router.post("/attempt", response_model=AttemptResult, responses=ERROR_RESPONSES)
async def submit_attempt(
    body: ExerciseAttempt,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Проверка ответа, обновление прогресса, следующее упражнение."""
    card = await db.scalar(
        select(Card)
        .join(Topic, Card.topic_id == Topic.id)
        .where(Card.id == body.card_id, Topic.user_id == current_user.id)
    )
    if card is None:
        raise CARD_NOT_FOUND
    if card.status != CardStatus.LEARNING:
        raise CARD_NOT_LEARNING

    # Строгая последовательность: отвечать можно только на текущую карточку темы
    current = await svc.get_current_card(db, card.topic_id)
    if current is None or current.id != card.id:
        raise AppError(409, "card_locked", "Master the current card first")

    # Строгая последовательность: можно отвечать только на текущее упражнение
    next_kind = await svc.get_next_exercise(db, card)
    if next_kind is None or body.exercise_kind != next_kind:
        raise WRONG_EXERCISE

    correct = svc.check_answer(card, body.exercise_kind, body.answer)

    session = await svc.get_or_create_session(db, current_user.id)
    result = await svc.record_attempt(
        db, card, body.exercise_kind, correct, body.used_hint, session
    )

    next_exercise: Exercise | None = None
    following_kind = await svc.get_next_exercise(db, card)
    if following_kind is not None:
        next_exercise = Exercise(
            **await svc.generate_exercise(db, card, following_kind)
        )

    return AttemptResult(
        correct=result["correct"],
        consecutive_correct=result["consecutive_correct"],
        required_consecutive=result["required_consecutive"],
        exercise_mastered=result["exercise_mastered"],
        card_mastered=result["card_mastered"],
        correct_answer=None if correct else svc.get_expected_answer(card, body.exercise_kind),
        next_exercise=next_exercise,
    )
