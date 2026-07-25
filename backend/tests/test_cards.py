"""Тесты CRUD тем и карточек + approve-флоу (issue #5)."""
import pytest


@pytest.mark.asyncio
async def test_topics_crud(client, auth_headers):
    # create
    resp = await client.post(
        "/api/topics",
        json={"name": "PostgreSQL", "description": "Базы данных"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    topic = resp.json()
    assert topic["name"] == "PostgreSQL"
    assert topic["cards_total"] == 0
    topic_id = topic["id"]

    # list
    resp = await client.get("/api/topics", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # get
    resp = await client.get(f"/api/topics/{topic_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "PostgreSQL"

    # update
    resp = await client.patch(
        f"/api/topics/{topic_id}",
        json={"name": "PostgreSQL Advanced"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "PostgreSQL Advanced"

    # delete
    resp = await client.delete(f"/api/topics/{topic_id}", headers=auth_headers)
    assert resp.status_code == 204

    # get after delete → 404
    resp = await client.get(f"/api/topics/{topic_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_topics_unauthorized(client):
    resp = await client.get("/api/topics")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_topic_not_found(client, auth_headers):
    resp = await client.get("/api/topics/9999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


@pytest.mark.asyncio
async def test_delete_topic_with_cards_forbidden(client, auth_headers):
    # create topic
    resp = await client.post(
        "/api/topics", json={"name": "Docker"}, headers=auth_headers
    )
    topic_id = resp.json()["id"]

    # add card
    resp = await client.post(
        "/api/cards",
        json={
            "topic_id": topic_id,
            "type": "term",
            "front_content": "Контейнер",
            "back_content": "Изолированная среда для приложения",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # delete topic → 409
    resp = await client.delete(f"/api/topics/{topic_id}", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "topic_not_empty"


@pytest.mark.asyncio
async def test_cards_crud_and_order(client, auth_headers):
    # create topic
    resp = await client.post(
        "/api/topics", json={"name": "Git"}, headers=auth_headers
    )
    topic_id = resp.json()["id"]

    # create cards → order_index 1, 2, 3
    for i in range(3):
        resp = await client.post(
            "/api/cards",
            json={
                "topic_id": topic_id,
                "type": "command",
                "front_content": f"Команда {i+1}",
                "back_content": f"git command {i+1}",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["order_index"] == i + 1
        assert resp.json()["status"] == "learning"  # manual → сразу в learning
        assert resp.json()["source"] == "manual"

    # list topic cards
    resp = await client.get(f"/api/topics/{topic_id}/cards", headers=auth_headers)
    assert resp.status_code == 200
    cards = resp.json()
    assert len(cards) == 3
    assert [c["order_index"] for c in cards] == [1, 2, 3]

    # update card
    card_id = cards[0]["id"]
    resp = await client.patch(
        f"/api/cards/{card_id}",
        json={"back_content": "git status"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["back_content"] == "git status"

    # delete card
    resp = await client.delete(f"/api/cards/{card_id}", headers=auth_headers)
    assert resp.status_code == 204

    # list after delete
    resp = await client.get(f"/api/topics/{topic_id}/cards", headers=auth_headers)
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_card_not_found(client, auth_headers):
    resp = await client.patch(
        "/api/cards/9999",
        json={"front_content": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_draft_approve_reject_flow(client, auth_headers, session_maker):
    from app.models.models import Card, CardSource, CardStatus, Topic

    # create topic via API
    resp = await client.post(
        "/api/topics", json={"name": "AI Drafts"}, headers=auth_headers
    )
    topic_id = resp.json()["id"]

    # create draft card directly in DB (simulating MCP/AI source)
    async with session_maker() as session:
        topic = await session.get(Topic, topic_id)
        draft = Card(
            topic_id=topic_id,
            type="term",
            front_content="Draft card",
            back_content="Draft answer",
            status=CardStatus.DRAFT,
            source=CardSource.MCP,
            order_index=0,
        )
        session.add(draft)
        await session.commit()
        draft_id = draft.id

    # list drafts
    resp = await client.get("/api/cards/drafts", headers=auth_headers)
    assert resp.status_code == 200
    drafts = resp.json()
    assert len(drafts) == 1
    assert drafts[0]["id"] == draft_id
    assert drafts[0]["source"] == "mcp"

    # approve → learning, order_index в конец
    resp = await client.post(f"/api/cards/{draft_id}/approve", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "learning"

    # check card is in learning queue
    resp = await client.get(f"/api/topics/{topic_id}/cards", headers=auth_headers)
    cards = resp.json()
    assert len(cards) == 1
    assert cards[0]["status"] == "learning"
    assert cards[0]["order_index"] == 1

    # approve again → 409
    resp = await client.post(f"/api/cards/{draft_id}/approve", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "not_a_draft"

    # create another draft and reject
    async with session_maker() as session:
        draft2 = Card(
            topic_id=topic_id,
            type="term",
            front_content="Bad draft",
            back_content="Bad answer",
            status=CardStatus.DRAFT,
            source=CardSource.AI,
            order_index=0,
        )
        session.add(draft2)
        await session.commit()
        draft2_id = draft2.id

    resp = await client.post(f"/api/cards/{draft2_id}/reject", headers=auth_headers)
    assert resp.status_code == 200
    assert "rejected" in resp.json()["message"]

    # drafts empty now
    resp = await client.get("/api/cards/drafts", headers=auth_headers)
    assert len(resp.json()) == 0
