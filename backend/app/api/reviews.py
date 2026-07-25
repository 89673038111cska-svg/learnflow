"""Интервальные повторения. Логика — в issue #7, сейчас 501."""
from typing import Any

from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.schemas import (
    ErrorResponse,
    ReviewCompleteRequest,
    ReviewCompleteResponse,
    ReviewResponse,
)

router = APIRouter()

NOT_IMPLEMENTED = AppError(501, "not_implemented", "Reviews будет реализован в issue #7")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
}


@router.get("/due", response_model=list[ReviewResponse], responses=ERROR_RESPONSES)
async def list_due_reviews():
    """Карточки к повторению: scheduled_at <= now, не completed."""
    raise NOT_IMPLEMENTED


@router.post(
    "/{review_id}/complete",
    response_model=ReviewCompleteResponse,
    responses=ERROR_RESPONSES,
)
async def complete_review(review_id: int, _: ReviewCompleteRequest):
    """success → следующий интервал; fail → карточка обратно в learning."""
    raise NOT_IMPLEMENTED
