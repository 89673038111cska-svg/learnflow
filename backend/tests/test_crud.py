"""Тесты CRUD тем и карточек + approve-флоу (issue #5)."""
import pytest


async def _create_topic(client, headers, name="Docker"):
    resp = await client.post(
        "/api/topics", json={"name": name, "description": "d"}, headers=headers
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_card(client, headers, topic_id, front="git push", back="отправить коммиты"):
    resp = await client.post(
        "/api/cards",
        json={
            "topic_id": topic_id,
            "type": "command",
            "front_content": front,
            "back_content": back,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_topics_crud(client, auth_headers):
    topic = await _create_topic(client, auth_headers)
    assert topic["cards_total"] == 0
    assert topic["cards_mastered"] == 0

    resp = await client.get("/api/topics", headers=auth_headers)
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == [topic["id"]]

    resp = await client.get(f"/api/topics/{topic['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Docker"

    resp = await client.patch(
        f"/api/topics/{topic['id']}", json={"name": "Docker Compose"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Docker Compose"

    resp = await client.delete(f"/api/topics/{topic['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/topics/{topic['id']}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


@pytest.mark.asyncio
async def test_delete_topic_with_cards_conflict(client, auth_headers):
    topic = await _create_topic(client, auth_headers)
    await _create_card(client, auth_headers, topic["id"])
    resp = await client.delete(f"/api/topics/{topic['id']}", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "topic_not_empty"


@pytest.mark.asyncio
async def test_topics_require_auth(client):
    resp = await client.get("/api/topics")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_manual_card_goes_to_learning_queue(client, auth_headers):
    topic = await _create_topic(client, auth_headers)
    card = await _create_card(client, auth_headers, topic["id"])
    assert card["status"] == "learning"
    assert card["source"] == "manual"
    assert card["order_index"] == 1

    card2 = await _create_card(client, auth_headers, topic["id"], "git pull", "забрать изменения")
    assert card2["order_index"] == 2

    resp = await client.get(f"/api/topics/{topic['id']}/cards", headers=auth_headers)
    assert resp.status_code == 200
    assert [c["order_index"] for c in resp.json()] == [1, 2]

    # счётчики темы обновились
    resp = await client.get(f"/api/topics/{topic['id']}", headers=auth_headers)
    assert resp.json()["cards_total"] == 2
    assert resp.json()["cards_mastered"] == 0


@pytest.mark.asyncio
async def test_card_update_and_delete(client, auth_headers):
    topic = await _create_topic(client, auth_headers)
    card = await _create_card(client, auth_headers, topic["id"])

    resp = await client.patch(
        f"/api/cards/{card['id']}", json={"front_content": "git push origin"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["front_content"] == "git push origin"

    resp = await client.delete(f"/api/cards/{card['id']}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.patch(
        f"/api/cards/{card['id']}", json={"front_content": "x"}, headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_create_card_unknown_topic(client, auth_headers):
    resp = await client.post(
        "/api/cards",
        json={"topic_id": 9999, "type": "term", "front_content": "a", "back_content": "b"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


# ---------------------------------------------------------------------------
# Drafts approve flow
# ---------------------------------------------------------------------------

async def _create_draft(client, headers, topic_id):
    """Черновик напрямую через БД-сессию приложения нельзя — создаём через API недоступно,
    поэтому эмулируем: вставляем draft через engine из conftest."""
    # используем session_maker из fixture через client dependency override — проще:
    # создаём карточку и затем помечаем draft прямым SQL через отдельное соединение.
    raise NotImplementedError


@pytest.mark.asyncio
async def test_approve_reject_flow(client, auth_headers, session_maker, test_user):
    from app.models.models import Card, CardSource, CardStatus, Topic
    from sqlalchemy import select

    topic = await _create_topic(client, auth_headers)

    # создаём draft как это сделал бы MCP-агент
    async with session_maker() as s:
        draft = Card(
            topic_id=topic["id"],
            type="term",
            front_content="container",
            back_content="изолированный процесс",
            status=CardStatus.DRAFT,
            source=CardSource.MCP,
            order_index=1,
        )
        s.add(draft)
        await s.commit()
        draft_id = draft.id

    # список черновиков
    resp = await client.get("/api/cards/drafts", headers=auth_headers)
    assert resp.status_code == 200
    assert [c["id"] for c in resp.json()] == [draft_id]

    # approve → learning, в конец очереди
    manual = await _create_card(client, auth_headers, topic["id"])
    resp = await client.post(f"/api/cards/{draft_id}/approve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "learning"

    resp = await client.get(f"/api/topics/{topic['id']}/cards", headers=auth_headers)
    cards = resp.json()
    approved = next(c for c in cards if c["id"] == draft_id)
    assert approved["status"] == "learning"
    assert approved["order_index"] > manual["order_index"]

    # повторный approve — конфликт
    resp = await client.post(f"/api/cards/{draft_id}/approve", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "not_a_draft"

    # reject другого черновика
    async with session_maker() as s:
        draft2 = Card(
            topic_id=topic["id"], type="term", front_content="x", back_content="y",
            status=CardStatus.DRAFT, source=CardSource.AI, order_index=99,
        )
        s.add(draft2)
        await s.commit()
        draft2_id = draft2.id

    resp = await client.post(f"/api/cards/{draft2_id}/reject", headers=auth_headers)
    assert resp.status_code == 200

    resp = await client.get("/api/cards/drafts", headers=auth_headers)
    assert resp.json() == []
