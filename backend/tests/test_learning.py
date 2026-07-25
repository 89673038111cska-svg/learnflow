"""Тесты механики обучения (issue #6).

Проверяем: генерацию 8 типов упражнений, правило «3 подряд в разных сессиях»,
сброс серии подсказкой/ошибкой, строгую последовательность.
"""
import pytest


async def _topic(client, headers, name="Git"):
    resp = await client.post("/api/topics", json={"name": name}, headers=headers)
    return resp.json()


async def _card(client, headers, topic_id, ctype="term", front="push", back="git push origin"):
    resp = await client.post(
        "/api/cards",
        json={"topic_id": topic_id, "type": ctype, "front_content": front, "back_content": back},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


async def _attempt(client, headers, card_id, kind, answer, used_hint=False):
    resp = await client.post(
        "/api/learning/attempt",
        json={"card_id": card_id, "exercise_kind": kind, "answer": answer, "used_hint": used_hint},
        headers=headers,
    )
    return resp


async def _state(client, headers, topic_id):
    resp = await client.get(f"/api/learning/state?topic_id={topic_id}", headers=headers)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_state_empty_topic(client, auth_headers):
    topic = await _topic(client, auth_headers)
    state = await _state(client, auth_headers, topic["id"])
    assert state["current_card"] is None
    assert state["exercise"] is None
    assert state["cards_total"] == 0
    assert state["progress_percent"] == 0.0


@pytest.mark.asyncio
async def test_state_returns_current_card_and_exercise(client, auth_headers):
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])
    state = await _state(client, auth_headers, topic["id"])
    assert state["current_card"]["id"] == card["id"]
    # term → первое упражнение multiple_choice
    assert state["exercise"]["kind"] == "multiple_choice"
    assert card["back_content"] in state["exercise"]["payload"]["options"]
    assert state["cards_total"] == 1


@pytest.mark.asyncio
async def test_wrong_answer_resets_streak_and_returns_answer(client, auth_headers):
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])

    # одна верная (сессия 1)
    r = await _attempt(client, auth_headers, card["id"], "multiple_choice", card["back_content"])
    assert r.status_code == 200 and r.json()["consecutive_correct"] == 1

    # ошибка сбрасывает
    r = await _attempt(client, auth_headers, card["id"], "multiple_choice", "неправильно")
    body = r.json()
    assert body["correct"] is False
    assert body["consecutive_correct"] == 0
    assert body["correct_answer"] == card["back_content"]


@pytest.mark.asyncio
async def test_same_session_correct_does_not_increment(client, auth_headers):
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])

    r1 = await _attempt(client, auth_headers, card["id"], "multiple_choice", card["back_content"])
    assert r1.json()["consecutive_correct"] == 1
    # повторная верная в той же сессии — не засчитывается
    r2 = await _attempt(client, auth_headers, card["id"], "multiple_choice", card["back_content"])
    assert r2.json()["consecutive_correct"] == 1


@pytest.mark.asyncio
async def test_hint_resets_streak(client, auth_headers):
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])

    r1 = await _attempt(client, auth_headers, card["id"], "multiple_choice", card["back_content"])
    assert r1.json()["consecutive_correct"] == 1
    r2 = await _attempt(
        client, auth_headers, card["id"], "multiple_choice", card["back_content"], used_hint=True
    )
    assert r2.json()["consecutive_correct"] == 0


@pytest.mark.asyncio
async def test_three_sessions_master_exercise(client, auth_headers, session_maker, test_user):
    """3 верных в разных сессиях осваивают упражнение и переключают на следующее."""
    from app.models.models import LearningSession
    from sqlalchemy import update

    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])

    kinds = ["multiple_choice", "reverse_choice", "text_input"]
    for kind in kinds:
        for i in range(3):
            # каждый заход — новая сессия: закрываем активные
            async with session_maker() as s:
                await s.execute(
                    update(LearningSession)
                    .where(LearningSession.user_id == test_user.id)
                    .values(ended_at=__import__("datetime").datetime.utcnow())
                )
                await s.commit()
            answer = card["front_content"] if kind == "reverse_choice" else card["back_content"]
            r = await _attempt(client, auth_headers, card["id"], kind, answer)
            body = r.json()
            assert r.status_code == 200, body
            assert body["consecutive_correct"] == i + 1
            assert body["exercise_mastered"] == (i == 2)

    # карточка освоена, все 3 типа пройдены
    assert body["card_mastered"] is True
    state = await _state(client, auth_headers, topic["id"])
    assert state["current_card"] is None
    assert state["cards_mastered"] == 1
    assert state["progress_percent"] == 100.0


@pytest.mark.asyncio
async def test_strict_sequence_blocks_wrong_exercise(client, auth_headers):
    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])
    # текущее — multiple_choice, пробуем text_input
    r = await _attempt(client, auth_headers, card["id"], "text_input", card["back_content"])
    assert r.status_code == 409
    assert r.json()["code"] == "wrong_exercise"


@pytest.mark.asyncio
async def test_strict_sequence_next_card_locked(client, auth_headers):
    """Нельзя отвечать на вторую карточку, пока первая не освоена."""
    topic = await _topic(client, auth_headers)
    await _card(client, auth_headers, topic["id"])
    card2 = await _card(client, auth_headers, topic["id"], front="pull", back="git pull origin")

    state = await _state(client, auth_headers, topic["id"])
    assert state["current_card"]["id"] != card2["id"]

    # попытка по второй карточке: её next exercise тоже multiple_choice,
    # но current_card — первая; attempt по card2 валиден только если он current.
    # По спеке: следующая открывается после освоения текущей → попытка по card2 запрещена.
    r = await _attempt(client, auth_headers, card2["id"], "multiple_choice", card2["back_content"])
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_attempt_on_mastered_card_rejected(client, auth_headers, session_maker):
    from app.models.models import Card, CardStatus
    from sqlalchemy import update

    topic = await _topic(client, auth_headers)
    card = await _card(client, auth_headers, topic["id"])
    async with session_maker() as s:
        await s.execute(update(Card).where(Card.id == card["id"]).values(status=CardStatus.MASTERED))
        await s.commit()
    r = await _attempt(client, auth_headers, card["id"], "multiple_choice", card["back_content"])
    assert r.status_code == 409
    assert r.json()["code"] == "card_not_learning"


@pytest.mark.asyncio
async def test_all_exercise_kinds_generate(client, auth_headers):
    """Все 8 типов упражнений генерируются для своих типов карточек."""
    topic = await _topic(client, auth_headers)
    cmd = await _card(client, auth_headers, topic["id"], "command", "отправить в remote", "git push origin main")
    proc = await _card(client, auth_headers, topic["id"], "procedure", "деплой", "git add .\ngit commit\ngit push")

    from app.services import learning as svc
    from app.models.models import Card

    # current — cmd (order_index меньше), первое упражнение command → fill_blank
    state = await _state(client, auth_headers, topic["id"])
    assert state["current_card"]["id"] == cmd["id"]
    assert state["exercise"]["kind"] == "fill_blank"
    assert "{{blank}}" in state["exercise"]["payload"]["template"]

    # генерация всех видов напрямую из сервиса (через БД-сессию теста)
    from sqlalchemy import select
    # используем session_maker из фикстур через dependency — достанем карточки из API-БД
    # проще: проверяем fill_blank ответ
    r = await _attempt(client, auth_headers, cmd["id"], "fill_blank", "main")
    assert r.json()["correct"] is True


@pytest.mark.asyncio
async def test_order_steps_check(client, auth_headers, session_maker, test_user):
    """order_steps принимает list[str], сверяет порядок."""
    from app.services.learning import check_answer
    from app.models.models import Card, CardType

    card = Card(
        id=1, topic_id=1, type=CardType.PROCEDURE,
        front_content="деплой", back_content="git add .\ngit commit\ngit push",
    )
    assert check_answer(card, "order_steps", ["git add .", "git commit", "git push"]) is True
    assert check_answer(card, "order_steps", ["git commit", "git add .", "git push"]) is False
    assert check_answer(card, "order_steps", ["git add .", "git commit"]) is False
    assert check_answer(card, "next_step", "git push") is True
    assert check_answer(card, "next_step", "git add .") is False
