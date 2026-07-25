"""Тесты MCP tools (issue #8): handlers напрямую, без MCP-транспорта."""
import json
import os

import pytest
import pytest_asyncio


@pytest.fixture
def mcp_env(monkeypatch):
    monkeypatch.setenv("LEARNFLOW_MCP_TOKEN", "dev_mcp_token_change_in_production")
    yield


async def _seed_user_topic(session_maker):
    from app.core.security import get_password_hash
    from app.models.models import Topic, User

    async with session_maker() as s:
        user = User(login="testuser", password_hash=get_password_hash("testpass123"))
        s.add(user)
        await s.flush()
        topic = Topic(user_id=user.id, name="Docker")
        s.add(topic)
        await s.commit()
        return user.id, topic.id


@pytest_asyncio.fixture
async def mcp_db(session_maker, monkeypatch):
    """Подменяем сессию MCP-сервера на тестовую БД."""
    from app.mcp import server as mcp_server

    monkeypatch.setattr(mcp_server, "_Session", session_maker)
    return mcp_server


@pytest.mark.asyncio
async def test_add_card_draft_creates_draft(mcp_env, mcp_db, session_maker):
    user_id, topic_id = await _seed_user_topic(session_maker)

    out = await mcp_db.add_card_draft(
        topic_id=topic_id, card_type="term",
        front="container", back="изолированный процесс",
    )
    data = json.loads(out)
    assert data["status"] == "draft"
    assert data["topic"] == "Docker"

    from app.models.models import Card, CardSource, CardStatus
    async with session_maker() as s:
        card = await s.get(Card, data["draft_id"])
        assert card.status == CardStatus.DRAFT
        assert card.source == CardSource.MCP


@pytest.mark.asyncio
async def test_add_card_draft_bad_type(mcp_env, mcp_db, session_maker):
    _, topic_id = await _seed_user_topic(session_maker)
    out = await mcp_db.add_card_draft(topic_id=topic_id, card_type="nope", front="a", back="b")
    assert out.startswith("error:")


@pytest.mark.asyncio
async def test_add_card_draft_unknown_topic(mcp_env, mcp_db, session_maker):
    await _seed_user_topic(session_maker)
    out = await mcp_db.add_card_draft(topic_id=999, card_type="term", front="a", back="b")
    assert "not found" in out


@pytest.mark.asyncio
async def test_list_topics(mcp_env, mcp_db, session_maker):
    _, topic_id = await _seed_user_topic(session_maker)
    out = json.loads(await mcp_db.list_topics())
    assert out == [{"id": topic_id, "name": "Docker", "cards_total": 0, "cards_mastered": 0}]


@pytest.mark.asyncio
async def test_get_learning_status(mcp_env, mcp_db, session_maker):
    from app.models.models import Card, CardStatus, CardType, CardSource

    _, topic_id = await _seed_user_topic(session_maker)
    async with session_maker() as s:
        s.add(Card(topic_id=topic_id, type=CardType.TERM, front_content="a", back_content="b",
                   status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1))
        s.add(Card(topic_id=topic_id, type=CardType.TERM, front_content="c", back_content="d",
                   status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=2))
        await s.commit()

    out = json.loads(await mcp_db.get_learning_status())
    assert out["topics"] == 1
    assert out["cards_learning"] == 1
    assert out["cards_mastered"] == 1
    assert out["cards_draft"] == 0
    assert out["reviews_due"] == 0


@pytest.mark.asyncio
async def test_tools_reject_without_token(mcp_db, session_maker, monkeypatch):
    monkeypatch.delenv("LEARNFLOW_MCP_TOKEN", raising=False)
    with pytest.raises(PermissionError):
        await mcp_db.list_topics()
    with pytest.raises(PermissionError):
        await mcp_db.add_card_draft(topic_id=1, card_type="term", front="a", back="b")
