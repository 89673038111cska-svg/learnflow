"""Интервальные повторения (issue #7): due-очередь + complete."""
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.models import Card, Review, Topic, User
from app.schemas.schemas import (
    CardResponse,
    ErrorResponse,
    ReviewCompleteRequest,
    ReviewCompleteResponse,
    ReviewResponse,
)
from app.services import learning as svc

router = APIRouter()

REVIEW_NOT_FOUND = AppError(404, "review_not_found", "Review not found")
REVIEW_ALREADY_DONE = AppError(409, "review_already_completed", "Review already completed")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.get("/due", response_model=list[ReviewResponse], responses=ERROR_RESPONSES)
async def list_due_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Карточки к повторению: scheduled_at <= now, не completed.

    Повторы идут параллельно с новым обучением — отдельная очередь.
    """
    from datetime import datetime

    reviews = (
        await db.scalars(
            select(Review)
            .join(Card, Review.card_id == Card.id)
            .join(Topic, Topic.id == Card.topic_id)
            .where(
                Topic.user_id == current_user.id,
                Review.completed_at.is_(None),
                Review.scheduled_at <= datetime.utcnow(),
            )
            .order_by(Review.scheduled_at)
        )
    ).all()

    result = []
    for r in reviews:
        card = await db.scalar(select(Card).where(Card.id == r.card_id))
        result.append(
            ReviewResponse(
                id=r.id,
                card_id=r.card_id,
                scheduled_at=r.scheduled_at,
                interval_days=r.interval_days,
                card=CardResponse.model_validate(card) if card else None,
            )
        )
    return result


@router.post(
    "/{review_id}/complete",
    response_model=ReviewCompleteResponse,
    responses=ERROR_RESPONSES,
)
async def complete_review(
    review_id: int,
    body: ReviewCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """success → следующий интервал (1d→3d→7d→14d→30d); fail → карточка обратно в learning."""
    review = await db.scalar(
        select(Review)
        .join(Card, Review.card_id == Card.id)
        .join(Topic, Topic.id == Card.topic_id)
        .where(Review.id == review_id, Topic.user_id == current_user.id)
    )
    if review is None:
        raise REVIEW_NOT_FOUND
    if review.completed_at is not None:
        raise REVIEW_ALREADY_DONE

    card = await db.scalar(select(Card).where(Card.id == review.card_id))
    await svc.complete_review(db, card, body.success)
    await db.refresh(review)

    next_review_at = None
    if body.success:
        nxt = await db.scalar(
            select(Review)
            .where(Review.card_id == card.id, Review.completed_at.is_(None))
            .order_by(Review.scheduled_at.desc())
            .limit(1)
        )
        next_review_at = nxt.scheduled_at if nxt else None

    return ReviewCompleteResponse(
        id=review.id,
        card_id=card.id,
        success=body.success,
        next_review_at=next_review_at,
        card_returned_to_learning=not body.success,
    )
