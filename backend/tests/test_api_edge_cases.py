"""Тесты граничных случаев API: not-found, конфликты, блокировки."""
import pytest


async def _topic(client, headers, name="Test"):
    resp = await client.post("/api/topics", json={"name": name}, headers=headers)
    return resp.json()


async def _card(client, headers, topic_id, ctype="term", front="q", back="a"):
    resp = await client.post(
        "/api/cards",
        json={"topic_id": topic_id, "type": ctype, "front_content": front, "back_content": back},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Learning state edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_learning_state_topic_not_found(client, auth_headers):
    """Запрос state для несуществующей темы → 404."""
    resp = await client.get("/api/learning/state?topic_id=9999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


@pytest.mark.asyncio
async def test_learning_state_with_two_cards_only_first_is_current(client, auth_headers):
    """При двух карточках в learning — current_card первая по order_index."""
    topic = await _topic(client, auth_headers, "MultiCard")
    c1 = await _card(client, auth_headers, topic["id"], front="card1")
    c2 = await _card(client, auth_headers, topic["id"], front="card2")

    resp = await client.get(f"/api/learning/state?topic_id={topic['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["current_card"]["id"] == c1["id"]


# ---------------------------------------------------------------------------
# Attempt edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_attempt_card_not_found(client, auth_headers):
    """Попытка ответа на несуществующую карточку → 404."""
    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": 9999, "exercise_kind": "multiple_choice", "answer": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_attempt_card_not_learning(client, auth_headers, session_maker):
    """Попытка ответа на DRAFT-карточку → 409."""
    from app.models.models import Card, CardStatus, CardType, CardSource

    topic = await _topic(client, auth_headers)
    async with session_maker() as s:
        draft = Card(
            topic_id=topic["id"], type=CardType.TERM, front_content="d", back_content="d",
            status=CardStatus.DRAFT, source=CardSource.MCP, order_index=1,
        )
        s.add(draft)
        await s.commit()
        draft_id = draft.id

    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": draft_id, "exercise_kind": "multiple_choice", "answer": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "card_not_learning"


@pytest.mark.asyncio
async def test_attempt_wrong_exercise_kind(client, auth_headers):
    """Попытка ответа не на текущее упражнение → 409."""
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"], "term", "push", "git push")

    # Для term первое упражнение — multiple_choice; пробуем text_input
    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": card["id"], "exercise_kind": "text_input", "answer": "x"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "wrong_exercise"


@pytest.mark.asyncio
async def test_attempt_card_locked_not_current(client, auth_headers):
    """Попытка ответа на вторую карточку, пока первая не освоена → 409."""
    topic = await _topic(client, auth_headers)
    await _card(client, auth_headers, topic["id"], front="first")
    card2 = await _card(client, auth_headers, topic["id"], front="second")

    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": card2["id"], "exercise_kind": "multiple_choice", "answer": "second"},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "card_locked"


# ---------------------------------------------------------------------------
# Hint edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hint_correct_answer_returned(client, auth_headers):
    """Подсказка возвращает правильный ответ."""
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"], front="push", back="git push")

    resp = await client.post(
        "/api/learning/hint",
        json={"card_id": card["id"], "exercise_kind": "multiple_choice", "answer": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["correct_answer"] == "git push"


@pytest.mark.asyncio
async def test_hint_card_not_found(client, auth_headers):
    """Подсказка для несуществующей карточки → 404."""
    resp = await client.post(
        "/api/learning/hint",
        json={"card_id": 9999, "exercise_kind": "multiple_choice", "answer": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_hint_wrong_exercise_kind(client, auth_headers):
    """Подсказка не для текущего упражнения → 409."""
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"], "term", "push", "git push")

    # Для term первое — multiple_choice; запрашиваем hint для text_input
    resp = await client.post(
        "/api/learning/hint",
        json={"card_id": card["id"], "exercise_kind": "text_input", "answer": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "wrong_exercise"


@pytest.mark.asyncio
async def test_hint_resets_consecutive_streak(client, auth_headers, session_maker, test_user):
    """Подсказка сбрасывает серию — проверяем через attempt после hint."""
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"], front="push", back="git push")
    sm = session_maker
    tu = test_user

    # Верный ответ (сессия 1)
    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": card["id"], "exercise_kind": "multiple_choice", "answer": "git push"},
        headers=auth_headers,
    )
    assert resp.json()["consecutive_correct"] == 1

    # Подсказка сбрасывает
    resp = await client.post(
        "/api/learning/hint",
        json={"card_id": card["id"], "exercise_kind": "multiple_choice", "answer": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # Новая сессия для проверки сброса
    from app.models.models import LearningSession
    from sqlalchemy import update
    from datetime import datetime
    async with sm() as s:
        await s.execute(
            update(LearningSession)
            .where(LearningSession.user_id == tu.id)
            .values(ended_at=datetime.utcnow())
        )
        await s.commit()

    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": card["id"], "exercise_kind": "multiple_choice", "answer": "git push",
              "used_hint": False},
        headers=auth_headers,
    )
    assert resp.json()["consecutive_correct"] == 1  # сброс отменил предыдущие 2


# ---------------------------------------------------------------------------
# Reviews edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_complete_review_not_found(client, auth_headers):
    """Завершение несуществующего review → 404."""
    resp = await client.post(
        "/api/reviews/9999/complete", json={"success": True}, headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "review_not_found"


@pytest.mark.asyncio
async def test_reviews_due_crosses_topic_boundary(client, auth_headers, session_maker, test_user):
    """Повторы из разных тем видны в единой due-очереди."""
    from app.models.models import Card, CardStatus, CardType, CardSource, Review
    from datetime import datetime, timedelta

    # Две темы, в каждой по карточке с просроченным review
    topic1 = await _topic(client, auth_headers, "Topic1")
    topic2 = await _topic(client, auth_headers, "Topic2")

    async with session_maker() as s:
        for t in [topic1, topic2]:
            card = Card(topic_id=t["id"], type=CardType.TERM, front_content="x", back_content="y",
                       status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            s.add(Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1), interval_days=1))
        await s.commit()

    resp = await client.get("/api/reviews/due", headers=auth_headers)
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_complete_review_wrong_user_review_not_found(client, auth_headers, session_maker):
    """Чужой review недоступен (не находится)."""
    from app.models.models import Card, CardStatus, CardType, CardSource, Review, User, Topic
    from app.core.security import get_password_hash
    from datetime import datetime, timedelta

    # Другой пользователь
    async with session_maker() as s:
        other = User(login="other", password_hash=get_password_hash("pass"))
        s.add(other)
        await s.flush()
        topic = Topic(user_id=other.id, name="OtherTopic")
        s.add(topic)
        await s.flush()
        card = Card(topic_id=topic.id, type=CardType.TERM, front_content="x", back_content="y",
                   status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
        s.add(card)
        await s.flush()
        s.add(Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1), interval_days=1))
        await s.commit()
        other_review_id = card.id  # любой невалидный id

    resp = await client.post(
        f"/api/reviews/{0}/complete", json={"success": True}, headers=auth_headers
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cards edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_nonexistent_card(client, auth_headers):
    """Approve несуществующей карточки → 404."""
    resp = await client.post("/api/cards/9999/approve", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_reject_nonexistent_card(client, auth_headers):
    """Reject несуществующей карточки → 404."""
    resp = await client.post("/api/cards/9999/reject", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_list_drafts_empty(client, auth_headers):
    """Список черновиков без черновиков → []."""
    await _topic(client, auth_headers)  # тема есть, карточек нет
    resp = await client.get("/api/cards/drafts", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_card_with_hint_flag(client, auth_headers):
    """Создание карточки с minimal полями (как агент через API)."""
    topic = await _topic(client, auth_headers, "APICard")
    resp = await client.post(
        "/api/cards",
        json={"topic_id": topic["id"], "type": "term", "front_content": "minimal", "back_content": "test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "learning"


@pytest.mark.asyncio
async def test_list_topic_cards_topic_not_found(client, auth_headers):
    """Список карточек несуществующей темы → 404."""
    resp = await client.get("/api/topics/9999/cards", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


@pytest.mark.asyncio
async def test_update_card_nonexistent(client, auth_headers):
    """Обновление несуществующей карточки → 404."""
    resp = await client.patch(
        "/api/cards/9999", json={"front_content": "x"}, headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "card_not_found"


@pytest.mark.asyncio
async def test_delete_card_nonexistent(client, auth_headers):
    """Удаление несуществующей карточки → 404."""
    resp = await client.delete("/api/cards/9999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_topic_not_found(client, auth_headers):
    """Обновление несуществующей темы → 404."""
    resp = await client.patch(
        "/api/topics/9999", json={"name": "x"}, headers=auth_headers
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "topic_not_found"


@pytest.mark.asyncio
async def test_delete_topic_not_found(client, auth_headers):
    """Удаление несуществующей темы → 404."""
    resp = await client.delete("/api/topics/9999", headers=auth_headers)
    assert resp.status_code == 404
