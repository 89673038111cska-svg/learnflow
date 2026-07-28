"""CRUD тем."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.models import Card, CardStatus, Topic, User
from app.schemas.schemas import ErrorResponse, TopicCreate, TopicResponse, TopicUpdate

logger = get_logger("topics")

router = APIRouter()

TOPIC_NOT_FOUND = AppError(404, "topic_not_found", "Topic not found")
TOPIC_NOT_EMPTY = AppError(
    409, "topic_not_empty", "Topic has cards — delete cards first"
)

ERROR_RESPONSES = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


async def _topic_with_counts(db: AsyncSession, topic: Topic) -> TopicResponse:
    total = await db.scalar(
        select(func.count(Card.id)).where(Card.topic_id == topic.id)
    )
    mastered = await db.scalar(
        select(func.count(Card.id)).where(
            Card.topic_id == topic.id, Card.status == CardStatus.MASTERED
        )
    )
    return TopicResponse(
        id=topic.id,
        name=topic.name,
        description=topic.description,
        created_at=topic.created_at,
        cards_total=total or 0,
        cards_mastered=mastered or 0,
    )


@router.get("", response_model=list[TopicResponse], responses=ERROR_RESPONSES)
async def list_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("list_topics", user_id=current_user.id)
    topics = (
        await db.scalars(
            select(Topic).where(Topic.user_id == current_user.id).order_by(Topic.id)
        )
    ).all()
    result = [await _topic_with_counts(db, t) for t in topics]
    logger.info("list_topics_done", user_id=current_user.id, count=len(result))
    return result


@router.post("", response_model=TopicResponse, status_code=201, responses=ERROR_RESPONSES)
async def create_topic(
    body: TopicCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("create_topic_start", user_id=current_user.id, name=body.name)
    topic = Topic(
        user_id=current_user.id, name=body.name, description=body.description
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    result = await _topic_with_counts(db, topic)
    logger.info("create_topic_done", user_id=current_user.id, topic_id=topic.id)
    return result


@router.get("/{topic_id}", response_model=TopicResponse, responses=ERROR_RESPONSES)
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("get_topic", user_id=current_user.id, topic_id=topic_id)
    topic = await db.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        logger.warning("get_topic_not_found", user_id=current_user.id, topic_id=topic_id)
        raise TOPIC_NOT_FOUND
    return await _topic_with_counts(db, topic)


@router.patch("/{topic_id}", response_model=TopicResponse, responses=ERROR_RESPONSES)
async def update_topic(
    topic_id: int,
    body: TopicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("update_topic_start", user_id=current_user.id, topic_id=topic_id)
    topic = await db.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        logger.warning("update_topic_not_found", user_id=current_user.id, topic_id=topic_id)
        raise TOPIC_NOT_FOUND

    if body.name is not None:
        topic.name = body.name
    if body.description is not None:
        topic.description = body.description

    await db.commit()
    await db.refresh(topic)
    result = await _topic_with_counts(db, topic)
    logger.info("update_topic_done", user_id=current_user.id, topic_id=topic_id)
    return result


@router.delete("/{topic_id}", status_code=204, responses=ERROR_RESPONSES)
async def delete_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info("delete_topic_start", user_id=current_user.id, topic_id=topic_id)
    topic = await db.scalar(
        select(Topic).where(Topic.id == topic_id, Topic.user_id == current_user.id)
    )
    if topic is None:
        logger.warning("delete_topic_not_found", user_id=current_user.id, topic_id=topic_id)
        raise TOPIC_NOT_FOUND

    has_cards = await db.scalar(
        select(func.count(Card.id)).where(Card.topic_id == topic_id)
    )
    if has_cards:
        logger.warning("delete_topic_not_empty", user_id=current_user.id, topic_id=topic_id, cards_count=has_cards)
        raise TOPIC_NOT_EMPTY

    await db.execute(delete(Topic).where(Topic.id == topic_id))
    await db.commit()
    logger.info("delete_topic_done", user_id=current_user.id, topic_id=topic_id)
