"""CRUD карточек + approve-флоу черновиков."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.models.models import Card, CardStatus, CardSource, Topic, User
from app.schemas.schemas import (
    CardCreate,
    CardResponse,
    CardUpdate,
    DraftActionResponse,
    ErrorResponse,
)

router = APIRouter()

CARD_NOT_FOUND = AppError(404, "card_not_found", "Card not found")
TOPIC_NOT_FOUND = AppError(404, "topic_not_found", "Topic not found")
NOT_DRAFT = AppError(409, "not_a_draft", "Card is not in draft status")

ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


async def _get_user_card(
    db: AsyncSession, card_id: int, user_id: int
) -> Card | None:
    return await db.scalar(
        select(Card)
        .join(Topic)
        .where(Card.id == card_id, Topic.user_id == user_id)
    )


async def _next_order_index(db: AsyncSession, topic_id: int) -> int:
    max_idx = await db.scalar(
        select(func.max(Card.order_index)).where(Card.topic_id == topic_id)
    )
    return (max_idx or 0) + 1


@router.get("/drafts", response_model=list[CardResponse], responses=ERROR_RESPONSES)
async def list_drafts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Все черновики пользователя (status=draft, любой source)."""
    cards = (
        await db.scalars(
            select(Card)
            .join(Topic)
            .where(Topic.user_id == current_user.id, Card.status == CardStatus.DRAFT)
            .order_by(Card.created_at)
        )
    ).all()
    return cards


@router.post("", response_model=CardResponse, status_code=201, responses=ERROR_RESPONSES)
async def create_card(
    body: CardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ручное создание → сразу в конец очереди learning."""
    topic = await db.scalar(
        select(Topic).where(Topic.id == body.topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        raise TOPIC_NOT_FOUND

    card = Card(
        topic_id=body.topic_id,
        type=body.type,
        front_content=body.front_content,
        back_content=body.back_content,
        status=CardStatus.LEARNING,
        source=CardSource.MANUAL,
        order_index=await _next_order_index(db, body.topic_id),
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


@router.patch("/{card_id}", response_model=CardResponse, responses=ERROR_RESPONSES)
async def update_card(
    card_id: int,
    body: CardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = await _get_user_card(db, card_id, current_user.id)
    if card is None:
        raise CARD_NOT_FOUND

    if body.front_content is not None:
        card.front_content = body.front_content
    if body.back_content is not None:
        card.back_content = body.back_content

    await db.commit()
    await db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = await _get_user_card(db, card_id, current_user.id)
    if card is None:
        raise CARD_NOT_FOUND

    await db.execute(delete(Card).where(Card.id == card_id))
    await db.commit()


@router.post("/{card_id}/approve", response_model=DraftActionResponse, responses=ERROR_RESPONSES)
async def approve_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """draft → learning (в конец очереди темы)."""
    card = await _get_user_card(db, card_id, current_user.id)
    if card is None:
        raise CARD_NOT_FOUND
    if card.status != CardStatus.DRAFT:
        raise NOT_DRAFT

    card.status = CardStatus.LEARNING
    card.order_index = await _next_order_index(db, card.topic_id)
    await db.commit()

    return DraftActionResponse(
        id=card.id, status=card.status, message="Card approved and moved to learning"
    )


@router.post("/{card_id}/reject", response_model=DraftActionResponse, responses=ERROR_RESPONSES)
async def reject_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Удаление черновика."""
    card = await _get_user_card(db, card_id, current_user.id)
    if card is None:
        raise CARD_NOT_FOUND
    if card.status != CardStatus.DRAFT:
        raise NOT_DRAFT

    await db.execute(delete(Card).where(Card.id == card_id))
    await db.commit()

    return DraftActionResponse(
        id=card_id, status=CardStatus.DRAFT, message="Draft rejected and deleted"
    )


# Список карточек темы — под topics-ресурсом
from fastapi import APIRouter as _APIRouter

topic_cards_router = _APIRouter()


@topic_cards_router.get(
    "/{topic_id}/cards", response_model=list[CardResponse], responses=ERROR_RESPONSES
)
async def list_topic_cards(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    topic = await db.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        raise TOPIC_NOT_FOUND

    cards = (
        await db.scalars(
            select(Card).where(Card.topic_id == topic_id).order_by(Card.order_index)
        )
    ).all()
    return cards
