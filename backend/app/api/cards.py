"""CRUD карточек + approve-флоу черновиков. Логика — в issue #5, сейчас 501."""
from typing import Any

from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.schemas import (
    CardCreate,
    CardResponse,
    CardUpdate,
    DraftActionResponse,
    ErrorResponse,
)

router = APIRouter()

NOT_IMPLEMENTED = AppError(501, "not_implemented", "Cards CRUD будет реализован в issue #5")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    501: {"model": ErrorResponse},
}


@router.get("/drafts", response_model=list[CardResponse], responses=ERROR_RESPONSES)
async def list_drafts():
    """Все черновики (status=draft, любой source: ai/mcp)."""
    raise NOT_IMPLEMENTED


@router.post("", response_model=CardResponse, status_code=201, responses=ERROR_RESPONSES)
async def create_card(_: CardCreate):
    """Ручное создание → сразу в конец очереди learning."""
    raise NOT_IMPLEMENTED


@router.patch("/{card_id}", response_model=CardResponse, responses=ERROR_RESPONSES)
async def update_card(card_id: int, _: CardUpdate):
    raise NOT_IMPLEMENTED


@router.delete("/{card_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_card(card_id: int):
    raise NOT_IMPLEMENTED


@router.post("/{card_id}/approve", response_model=DraftActionResponse, responses=ERROR_RESPONSES)
async def approve_card(card_id: int):
    """draft → learning (в конец очереди темы)."""
    raise NOT_IMPLEMENTED


@router.post("/{card_id}/reject", response_model=DraftActionResponse, responses=ERROR_RESPONSES)
async def reject_card(card_id: int):
    """Удаление черновика."""
    raise NOT_IMPLEMENTED


# Список карточек темы живёт под topics-ресурсом
from fastapi import APIRouter as _APIRouter

topic_cards_router = _APIRouter()


@topic_cards_router.get(
    "/{topic_id}/cards", response_model=list[CardResponse], responses=ERROR_RESPONSES
)
async def list_topic_cards(topic_id: int):
    raise NOT_IMPLEMENTED
