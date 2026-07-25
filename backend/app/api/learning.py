"""Механика обучения. Логика — в issue #6, сейчас 501."""
from typing import Any

from fastapi import APIRouter, Query

from app.core.errors import AppError
from app.schemas.schemas import (
    AttemptResult,
    ErrorResponse,
    ExerciseAttempt,
    LearningStateResponse,
)

router = APIRouter()

NOT_IMPLEMENTED = AppError(501, "not_implemented", "Learning будет реализован в issue #6")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
}


@router.get("/state", response_model=LearningStateResponse, responses=ERROR_RESPONSES)
async def get_learning_state(topic_id: int = Query(...)):
    """Текущая карточка темы + упражнение + reviews_due + прогресс."""
    raise NOT_IMPLEMENTED


@router.post("/attempt", response_model=AttemptResult, responses=ERROR_RESPONSES)
async def submit_attempt(_: ExerciseAttempt):
    """Проверка ответа, обновление прогресса, следующее упражнение."""
    raise NOT_IMPLEMENTED
