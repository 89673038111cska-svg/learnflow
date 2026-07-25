"""Тесты интервальных повторений (issue #7)."""
from datetime import datetime, timedelta

import pytest


async def _master_card(client, headers, session_maker, user_id, topic_id):
    """Создаёт карточку и помечает её освоенной + review, просроченный к now."""
    from app.models.models import Card, CardStatus, CardType, CardSource, Review

    async with session_maker() as s:
        card = Card(
            topic_id=topic_id, type=CardType.TERM, front_content="image",
            back_content="шаблон контейнера", status=CardStatus.MASTERED,
            source=CardSource.MANUAL, order_index=1,
        )
        s.add(card)
        await s.flush()
        review = Review(
            card_id=card.id,
            scheduled_at=datetime.utcnow() - timedelta(hours=1),
            interval_days=1,
        )
        s.add(review)
        await s.commit()
        return card.id, review.id


async def _topic(client, headers):
    resp = await client.post("/api/topics", json={"name": "Docker"}, headers=headers)
    return resp.json()


@pytest.mark.asyncio
async def test_due_reviews_listed(client, auth_headers, session_maker, test_user):
    topic = await _topic(client, auth_headers)
    card_id, review_id = await _master_card(client, auth_headers, session_maker, test_user.id, topic["id"])

    resp = await client.get("/api/reviews/due", headers=auth_headers)
    assert resp.status_code == 200
    due = resp.json()
    assert len(due) == 1
    assert due[0]["id"] == review_id
    assert due[0]["card"]["id"] == card_id
    assert due[0]["card"]["front_content"] == "image"

    # reviews_due виден в learning state
    resp = await client.get(f"/api/learning/state?topic_id={topic['id']}", headers=auth_headers)
    assert resp.json()["reviews_due"] == 1


@pytest.mark.asyncio
async def test_future_review_not_due(client, auth_headers, session_maker, test_user):
    from app.models.models import Card, CardStatus, CardType, CardSource, Review

    topic = await _topic(client, auth_headers)
    async with session_maker() as s:
        card = Card(topic_id=topic["id"], type=CardType.TERM, front_content="x",
                    back_content="y", status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
        s.add(card)
        await s.flush()
        s.add(Review(card_id=card.id, scheduled_at=datetime.utcnow() + timedelta(days=1), interval_days=1))
        await s.commit()

    resp = await client.get("/api/reviews/due", headers=auth_headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_success_schedules_next_interval(client, auth_headers, session_maker, test_user):
    topic = await _topic(client, auth_headers)
    card_id, review_id = await _master_card(client, auth_headers, session_maker, test_user.id, topic["id"])

    resp = await client.post(
        f"/api/reviews/{review_id}/complete", json={"success": True}, headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["card_returned_to_learning"] is False
    assert body["next_review_at"] is not None

    # следующий интервал — 3 дня
    from app.models.models import Review
    from sqlalchemy import select
    async with session_maker() as s:
        nxt = await s.scalar(
            select(Review).where(Review.card_id == card_id, Review.completed_at.is_(None))
        )
        assert nxt.interval_days == 3
        assert nxt.scheduled_at > datetime.utcnow() + timedelta(days=2)

    # due-очередь пуста
    resp = await client.get("/api/reviews/due", headers=auth_headers)
    assert resp.json() == []


@pytest.mark.asyncio
async def test_fail_returns_card_to_learning(client, auth_headers, session_maker, test_user):
    topic = await _topic(client, auth_headers)
    card_id, review_id = await _master_card(client, auth_headers, session_maker, test_user.id, topic["id"])

    resp = await client.post(
        f"/api/reviews/{review_id}/complete", json={"success": False}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["card_returned_to_learning"] is True

    # карточка вернулась в learning и стала текущей
    resp = await client.get(f"/api/learning/state?topic_id={topic['id']}", headers=auth_headers)
    state = resp.json()
    assert state["current_card"]["id"] == card_id
    assert state["current_card"]["status"] == "learning"


@pytest.mark.asyncio
async def test_complete_twice_conflict(client, auth_headers, session_maker, test_user):
    topic = await _topic(client, auth_headers)
    _, review_id = await _master_card(client, auth_headers, session_maker, test_user.id, topic["id"])
    await client.post(f"/api/reviews/{review_id}/complete", json={"success": True}, headers=auth_headers)
    resp = await client.post(
        f"/api/reviews/{review_id}/complete", json={"success": True}, headers=auth_headers
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "review_already_completed"


@pytest.mark.asyncio
async def test_interval_progression(client, auth_headers, session_maker, test_user):
    """1d → 3d → 7d: последовательность интервалов."""
    from app.models.models import Review
    from sqlalchemy import select, update

    topic = await _topic(client, auth_headers)
    card_id, review_id = await _master_card(client, auth_headers, session_maker, test_user.id, topic["id"])

    expected = [3, 7, 14]
    current_id = review_id
    for interval in expected:
        resp = await client.post(
            f"/api/reviews/{current_id}/complete", json={"success": True}, headers=auth_headers
        )
        assert resp.status_code == 200
        async with session_maker() as s:
            nxt = await s.scalar(
                select(Review).where(Review.card_id == card_id, Review.completed_at.is_(None))
            )
            assert nxt.interval_days == interval
            current_id = nxt.id
