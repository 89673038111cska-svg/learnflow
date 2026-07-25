"""MCP Server for LearnFlow (issue #8).

Tools:
- add_card_draft: карточка-черновик (status=draft, source=mcp) на approve пользователю
- list_topics: список тем с id (нужен topic_id для add_card_draft)
- get_learning_status: сводка — темы, в обучении/освоено, reviews due

Запуск (stdio):  python -m app.mcp.server
Аутентификация: токен в env MCP_API_TOKEN должен совпадать с настройкой бэкенда;
в конфиге MCP-клиента (Hermes) токен передаётся через env.
"""
import json
import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

mcp = FastMCP("learnflow")

_engine = create_async_engine(settings.DATABASE_URL)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


def _check_token() -> None:
    """Проверка токена агента. В stdio-режиме токен приходит через env LEARNFLOW_MCP_TOKEN."""
    expected = settings.MCP_API_TOKEN
    provided = os.environ.get("LEARNFLOW_MCP_TOKEN", "")
    if not provided or provided != expected:
        raise PermissionError("Invalid or missing MCP API token")


async def _single_user_id(session) -> int:
    """MVP — single user: берём первого пользователя."""
    from app.models.models import User

    user_id = await session.scalar(select(User.id).order_by(User.id).limit(1))
    if user_id is None:
        raise RuntimeError("No users in database — run seed script first")
    return user_id


@mcp.tool()
async def add_card_draft(
    topic_id: int,
    card_type: str,
    front: str,
    back: str,
    metadata: str | None = None,
) -> str:
    """Create a card draft for user approval.

    Args:
        topic_id: ID темы (получить через list_topics)
        card_type: term | command | procedure
        front: вопрос / термин / задача
        back: ответ / определение / решение (для procedure — JSON {"steps": [...]} или по строке на шаг)
        metadata: опциональный JSON с контекстом (источник, ссылка и т.п.)
    """
    _check_token()
    from app.models.models import Card, CardSource, CardStatus, CardType, Topic

    try:
        ctype = CardType(card_type)
    except ValueError:
        return f"error: card_type must be one of: term, command, procedure (got '{card_type}')"

    async with _Session() as session:
        user_id = await _single_user_id(session)
        topic = await session.scalar(
            select(Topic).where(Topic.id == topic_id, Topic.user_id == user_id)
        )
        if topic is None:
            return f"error: topic {topic_id} not found"

        max_order = await session.scalar(
            select(func.max(Card.order_index)).where(Card.topic_id == topic_id)
        )
        card = Card(
            topic_id=topic_id,
            type=ctype,
            front_content=front,
            back_content=back,
            status=CardStatus.DRAFT,
            source=CardSource.MCP,
            order_index=(max_order or 0) + 1,
        )
        session.add(card)
        await session.commit()
        return json.dumps(
            {"draft_id": card.id, "topic": topic.name, "status": "draft"},
            ensure_ascii=False,
        )


@mcp.tool()
async def list_topics() -> str:
    """List all learning topics with ids and card stats."""
    _check_token()
    from app.models.models import Card, CardStatus, Topic

    async with _Session() as session:
        user_id = await _single_user_id(session)
        topics = (
            await session.scalars(
                select(Topic).where(Topic.user_id == user_id).order_by(Topic.id)
            )
        ).all()
        result = []
        for t in topics:
            total = await session.scalar(
                select(func.count(Card.id)).where(Card.topic_id == t.id)
            ) or 0
            mastered = await session.scalar(
                select(func.count(Card.id)).where(
                    Card.topic_id == t.id, Card.status == CardStatus.MASTERED
                )
            ) or 0
            result.append(
                {"id": t.id, "name": t.name, "cards_total": total, "cards_mastered": mastered}
            )
        return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def get_learning_status() -> str:
    """Get learning summary: topics, cards learning/mastered/draft, reviews due."""
    _check_token()
    from app.models.models import Card, CardStatus, Review, Topic

    async with _Session() as session:
        user_id = await _single_user_id(session)

        counts = {}
        for status in CardStatus:
            counts[status.value] = await session.scalar(
                select(func.count(Card.id))
                .join(Topic, Card.topic_id == Topic.id)
                .where(Topic.user_id == user_id, Card.status == status)
            ) or 0

        reviews_due = await session.scalar(
            select(func.count(Review.id))
            .join(Card, Review.card_id == Card.id)
            .join(Topic, Topic.id == Card.topic_id)
            .where(
                Topic.user_id == user_id,
                Review.completed_at.is_(None),
                Review.scheduled_at <= datetime.utcnow(),
            )
        ) or 0

        topics_count = await session.scalar(
            select(func.count(Topic.id)).where(Topic.user_id == user_id)
        ) or 0

        return json.dumps(
            {
                "topics": topics_count,
                "cards_draft": counts["draft"],
                "cards_learning": counts["learning"],
                "cards_mastered": counts["mastered"],
                "reviews_due": reviews_due,
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run()
