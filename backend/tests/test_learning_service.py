"""Модульные тесты learning-сервиса: проверка ответов, прогресс, генерация упражнений."""
import json
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.models import (
    Card, CardProgress, CardStatus, CardType, CardSource,
    LearningSession, Review, Topic,
)
from app.services import learning as svc


# ---------------------------------------------------------------------------
# normalize_answer
# ---------------------------------------------------------------------------

class TestNormalizeAnswer:
    def test_trims_and_lowercases(self):
        assert svc.normalize_answer("  Hello World  ") == "hello world"

    def test_collapses_whitespace(self):
        assert svc.normalize_answer("git   push   origin") == "git push origin"

    def test_empty_string(self):
        assert svc.normalize_answer("") == ""


# ---------------------------------------------------------------------------
# get_exercises_for_card
# ---------------------------------------------------------------------------

class TestGetExercisesForCard:
    def test_term_exercises(self):
        card = Card(type=CardType.TERM)
        assert svc.get_exercises_for_card(card) == ["multiple_choice", "reverse_choice", "text_input"]

    def test_command_exercises(self):
        card = Card(type=CardType.COMMAND)
        assert svc.get_exercises_for_card(card) == ["fill_blank", "write_command", "find_bug"]

    def test_procedure_exercises(self):
        card = Card(type=CardType.PROCEDURE)
        assert svc.get_exercises_for_card(card) == ["order_steps", "next_step"]


# ---------------------------------------------------------------------------
# check_answer
# ---------------------------------------------------------------------------

class TestCheckAnswer:
    def test_multiple_choice_correct(self):
        card = Card(back_content="git push origin")
        assert svc.check_answer(card, "multiple_choice", "git push origin") is True

    def test_multiple_choice_incorrect(self):
        card = Card(back_content="git push origin")
        assert svc.check_answer(card, "multiple_choice", "git pull") is False

    def test_reverse_choice_correct(self):
        card = Card(front_content="отправить коммиты", back_content="git push")
        assert svc.check_answer(card, "reverse_choice", "отправить коммиты") is True

    def test_text_input_correct(self):
        card = Card(back_content="изолированная среда")
        assert svc.check_answer(card, "text_input", "изолированная среда") is True

    def test_fill_blank_correct(self):
        card = Card(back_content="git push origin main")
        assert svc.check_answer(card, "fill_blank", "main") is True

    def test_fill_blank_incorrect(self):
        card = Card(back_content="git push origin main")
        assert svc.check_answer(card, "fill_blank", "origin") is False

    def test_order_steps_correct_order(self):
        card = Card(back_content="git add .\ngit commit\ngit push")
        assert svc.check_answer(card, "order_steps", ["git add .", "git commit", "git push"]) is True

    def test_order_steps_wrong_order(self):
        card = Card(back_content="git add .\ngit commit\ngit push")
        assert svc.check_answer(card, "order_steps", ["git commit", "git add .", "git push"]) is False

    def test_order_steps_wrong_count(self):
        card = Card(back_content="git add .\ngit commit\ngit push")
        assert svc.check_answer(card, "order_steps", ["git add .", "git commit"]) is False

    def test_next_step_correct(self):
        card = Card(back_content="git add .\ngit commit\ngit push")
        assert svc.check_answer(card, "next_step", "git push") is True

    def test_next_step_incorrect(self):
        card = Card(back_content="git add .\ngit commit\ngit push")
        assert svc.check_answer(card, "next_step", "git add .") is False

    def test_write_command_correct(self):
        card = Card(back_content="docker compose up")
        assert svc.check_answer(card, "write_command", "docker compose up") is True

    def test_find_bug_correct(self):
        card = Card(back_content="correct code")
        assert svc.check_answer(card, "find_bug", "correct code") is True

    def test_not_a_list_for_list_answer(self):
        card = Card(back_content="step1\nstep2")
        assert svc.check_answer(card, "order_steps", "not a list") is False


# ---------------------------------------------------------------------------
# get_expected_answer
# ---------------------------------------------------------------------------

class TestGetExpectedAnswer:
    def test_multiple_choice(self):
        card = Card(back_content="docker run")
        assert svc.get_expected_answer(card, "multiple_choice") == "docker run"

    def test_reverse_choice(self):
        card = Card(front_content="запустить контейнер")
        assert svc.get_expected_answer(card, "reverse_choice") == "запустить контейнер"

    def test_fill_blank(self):
        card = Card(back_content="git push origin main")
        assert svc.get_expected_answer(card, "fill_blank") == "main"

    def test_order_steps(self):
        card = Card(back_content="step1\nstep2\nstep3")
        assert svc.get_expected_answer(card, "order_steps") == ["step1", "step2", "step3"]

    def test_next_step(self):
        card = Card(back_content="step1\nstep2\nstep3")
        assert svc.get_expected_answer(card, "next_step") == "step3"

    def test_text_input(self):
        card = Card(back_content="ответ")
        assert svc.get_expected_answer(card, "text_input") == "ответ"


# ---------------------------------------------------------------------------
# get_steps / get_blank_answer / get_fill_blank_template
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_get_steps_from_lines(self):
        card = Card(back_content="step a\nstep b\nstep c")
        assert svc.get_steps(card) == ["step a", "step b", "step c"]

    def test_get_steps_from_json(self):
        card = Card(back_content=json.dumps({"steps": ["build", "test", "deploy"]}))
        assert svc.get_steps(card) == ["build", "test", "deploy"]

    def test_get_steps_from_json_missing_steps_key(self):
        card = Card(back_content=json.dumps({"not_steps": ["x"]}))
        assert svc.get_steps(card) == [json.dumps({"not_steps": ["x"]})]

    def test_get_steps_empty(self):
        card = Card(back_content="")
        assert svc.get_steps(card) == []

    def test_get_blank_answer(self):
        card = Card(back_content="git push origin main")
        assert svc.get_blank_answer(card) == "main"

    def test_get_blank_answer_single_token(self):
        card = Card(back_content="hello")
        assert svc.get_blank_answer(card) == "hello"

    def test_get_fill_blank_template(self):
        card = Card(back_content="git push origin main")
        assert "{{blank}}" in svc.get_fill_blank_template(card)
        assert "main" not in svc.get_fill_blank_template(card)

    def test_get_fill_blank_template_single_token(self):
        card = Card(back_content="hello")
        assert svc.get_fill_blank_template(card) == "{{blank}}"


# ---------------------------------------------------------------------------
# Интеграционные тесты сервиса — требуют session_maker
# ---------------------------------------------------------------------------

class TestServiceWithDB:
    """Тесты, использующие реальную БД через session_maker."""

    @pytest.mark.asyncio
    async def test_get_or_create_session_new(self, session_maker, test_user):
        async with session_maker() as s:
            session = await svc.get_or_create_session(s, test_user.id)
            assert session.id is not None
            assert session.user_id == test_user.id
            assert session.ended_at is None

    @pytest.mark.asyncio
    async def test_get_or_create_session_reuses_active(self, session_maker, test_user):
        async with session_maker() as s:
            first = await svc.get_or_create_session(s, test_user.id)
            second = await svc.get_or_create_session(s, test_user.id)
            assert first.id == second.id  # reuse

    @pytest.mark.asyncio
    async def test_get_or_create_session_creates_new_after_old_closes(self, session_maker, test_user):
        async with session_maker() as s:
            first = await svc.get_or_create_session(s, test_user.id)
            # Закрываем
            first.ended_at = datetime.utcnow()
            await s.flush()
            second = await svc.get_or_create_session(s, test_user.id)
            assert second.id != first.id

    @pytest.mark.asyncio
    async def test_get_current_card_returns_first_learning(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            c1 = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                      status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=2)
            c2 = Card(topic_id=topic.id, type=CardType.TERM, front_content="c", back_content="d",
                      status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add_all([c1, c2])
            await s.commit()

            card = await svc.get_current_card(s, topic.id)
            assert card is not None
            assert card.id == c2.id  # меньший order_index

    @pytest.mark.asyncio
    async def test_get_current_card_returns_none_when_all_mastered(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            c = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                     status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(c)
            await s.commit()
            assert await svc.get_current_card(s, topic.id) is None

    @pytest.mark.asyncio
    async def test_get_next_exercise_first_time(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            nxt = await svc.get_next_exercise(s, card)
            assert nxt == "multiple_choice"  # первое упражнение для term

    @pytest.mark.asyncio
    async def test_record_attempt_correct_new_progress(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            session = await svc.get_or_create_session(s, test_user.id)
            await s.commit()

            result = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
            assert result["correct"] is True
            assert result["consecutive_correct"] == 1
            assert result["exercise_mastered"] is False
            assert result["card_mastered"] is False

    @pytest.mark.asyncio
    async def test_record_attempt_hint_resets_streak(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            session = await svc.get_or_create_session(s, test_user.id)
            await s.flush()
            # Один верный ответ
            r1 = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
            assert r1["consecutive_correct"] == 1
            # Подсказка сбрасывает
            r2 = await svc.record_attempt(s, card, "multiple_choice", True, True, session)
            assert r2["consecutive_correct"] == 0

    @pytest.mark.asyncio
    async def test_record_attempt_increments_in_same_session(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            session = await svc.get_or_create_session(s, test_user.id)
            await s.flush()
            r1 = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
            assert r1["consecutive_correct"] == 1
            # Та же сессия — теперь засчитывается
            r2 = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
            assert r2["consecutive_correct"] == 2

    @pytest.mark.asyncio
    async def test_record_attempt_wrong_resets_streak(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            session = await svc.get_or_create_session(s, test_user.id)
            await s.flush()
            r1 = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
            assert r1["consecutive_correct"] == 1
            # Ошибка сбрасывает
            r2 = await svc.record_attempt(s, card, "multiple_choice", False, False, session)
            assert r2["consecutive_correct"] == 0

    @pytest.mark.asyncio
    async def test_three_correct_in_different_sessions_masters_exercise(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()

        # 3 попытки в 3 разных сессиях
        for i in range(3):
            async with session_maker() as s:
                # Создаём новую сессию
                s.add(LearningSession(user_id=test_user.id))
                await s.flush()
                session = await s.scalar(
                    select(LearningSession).where(LearningSession.user_id == test_user.id,
                                                  LearningSession.ended_at.is_(None))
                    .order_by(LearningSession.started_at.desc()).limit(1)
                )
                # Отключаем старые (если есть)
                old_sessions = await s.scalars(
                    select(LearningSession).where(LearningSession.user_id == test_user.id,
                                                  LearningSession.id != session.id)
                )
                for old in old_sessions:
                    old.ended_at = datetime.utcnow()

                result = await svc.record_attempt(s, card, "multiple_choice", True, False, session)
                assert result["consecutive_correct"] == i + 1
                if i == 2:
                    assert result["exercise_mastered"] is True
                await s.commit()

    @pytest.mark.asyncio
    async def test_record_attempt_masters_card_and_schedules_review(self, session_maker, test_user):
        """После освоения всех упражнений карточка помечается MASTERED и создаётся Review."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()

        # Осваиваем все 3 упражнения для TERM
        for ex_type in ["multiple_choice", "reverse_choice", "text_input"]:
            for _ in range(3):
                async with session_maker() as s:
                    card_loaded = await s.get(Card, card.id)
                    # Новая сессия
                    session = LearningSession(user_id=test_user.id)
                    s.add(session)
                    await s.flush()
                    await svc.record_attempt(s, card_loaded, ex_type, True, False, session)
                    await s.commit()

        # Проверяем: карточка MASTERED, Review создан
        async with session_maker() as s:
            updated = await s.get(Card, card.id)
            assert updated.status == CardStatus.MASTERED
            review = await s.scalar(select(Review).where(Review.card_id == card.id))
            assert review is not None
            assert review.interval_days == 1  # первый интервал

    @pytest.mark.asyncio
    async def test_complete_review_success_next_interval(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            review = Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1), interval_days=1)
            s.add(review)
            await s.commit()
            card_loaded = await s.get(Card, card.id)
            await svc.complete_review(s, card_loaded, True)

        async with session_maker() as s:
            # Проверяем completed + новый review
            old = await s.scalar(select(Review).where(Review.card_id == card.id, Review.completed_at.isnot(None)))
            assert old is not None
            assert old.success is True
            nxt = await s.scalar(select(Review).where(Review.card_id == card.id, Review.completed_at.is_(None)))
            assert nxt is not None
            assert nxt.interval_days == 3  # следующий интервал
            assert nxt.scheduled_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_complete_review_failure_returns_to_learning(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            progress = CardProgress(card_id=card.id, exercise_type="multiple_choice",
                                    consecutive_correct=3, mastered_at=datetime.utcnow())
            s.add(progress)
            review = Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1), interval_days=1)
            s.add(review)
            await s.commit()

        # Успешно вызываем complete_review с failure
        # Захватываем review до вызова, т.к. complete_review работает с переданной сессией
        async with session_maker() as s:
            card_loaded = await s.get(Card, card.id)
            await svc.complete_review(s, card_loaded, False)

        async with session_maker() as s:
            updated = await s.get(Card, card.id)
            assert updated.status == CardStatus.LEARNING
            progress = await s.scalar(select(CardProgress).where(CardProgress.card_id == card.id))
            assert progress.consecutive_correct == 2  # max(0, 3-1)
            assert progress.mastered_at is None

    @pytest.mark.asyncio
    async def test_generate_multiple_choice_exercise(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="q", back_content="correct",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()

            ex = await svc.generate_exercise(s, card, "multiple_choice")
            assert ex["kind"] == "multiple_choice"
            assert "options" in ex["payload"]
            assert "correct" in ex["payload"]["options"]

    @pytest.mark.asyncio
    async def test_generate_text_input(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="q", back_content="a",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "text_input")
            assert ex["kind"] == "text_input"
            assert ex["payload"]["prompt"] == "q"

    @pytest.mark.asyncio
    async def test_generate_fill_blank(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.COMMAND, front_content="push", back_content="git push origin main",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "fill_blank")
            assert ex["kind"] == "fill_blank"
            assert "{{blank}}" in ex["payload"]["template"]

    @pytest.mark.asyncio
    async def test_generate_order_steps(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.PROCEDURE, front_content="deploy",
                        back_content="build\ntest\ndeploy",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "order_steps")
            assert ex["kind"] == "order_steps"
            assert len(ex["payload"]["shuffled_steps"]) == 3

    @pytest.mark.asyncio
    async def test_generate_next_step(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.PROCEDURE, front_content="deploy",
                        back_content="step1\nstep2\nstep3",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "next_step")
            assert ex["kind"] == "next_step"
            assert ex["payload"]["given_steps"] == ["step1", "step2"]

    @pytest.mark.asyncio
    async def test_generate_reverse_choice(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="front_text", back_content="back_text",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "reverse_choice")
            assert ex["kind"] == "reverse_choice"
            assert "options" in ex["payload"]

    @pytest.mark.asyncio
    async def test_distractors_exclude_own_card(self, session_maker, test_user):
        """Дистракторы не включают правильный ответ."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            c1 = Card(topic_id=topic.id, type=CardType.TERM, front_content="q1", back_content="correct",
                      status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            c2 = Card(topic_id=topic.id, type=CardType.TERM, front_content="q2", back_content="distractor1",
                      status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=2)
            c3 = Card(topic_id=topic.id, type=CardType.TERM, front_content="q3", back_content="distractor2",
                      status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=3)
            s.add_all([c1, c2, c3])
            await s.commit()

            dist = await svc._distractors(s, c1, "back")
            assert "correct" not in dist
            assert len(dist) == 2

    @pytest.mark.asyncio
    async def test_due_reviews_empty(self, session_maker, test_user):
        async with session_maker() as s:
            cards = await svc.get_due_reviews(s, test_user.id)
            assert cards == []

    @pytest.mark.asyncio
    async def test_due_reviews_returns_due(self, session_maker, test_user):
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            review = Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1), interval_days=1)
            s.add(review)
            await s.commit()
            due = await svc.get_due_reviews(s, test_user.id)
            assert len(due) == 1
            assert due[0].id == card.id

    @pytest.mark.asyncio
    async def test_get_next_exercise_all_mastered(self, session_maker, test_user):
        """Когда все упражнения освоены, get_next_exercise возвращает None."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            for ex_type in ["multiple_choice", "reverse_choice", "text_input"]:
                s.add(CardProgress(card_id=card.id, exercise_type=ex_type, consecutive_correct=3, mastered_at=datetime.utcnow()))
            await s.commit()
            assert await svc.get_next_exercise(s, card) is None

    @pytest.mark.asyncio
    async def test_generate_unknown_exercise_type(self, session_maker, test_user):
        """Неизвестный тип упражнения возвращает базовый prompt."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="q", back_content="a",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "unknown_type")
            assert ex["kind"] == "unknown_type"
            assert ex["payload"]["prompt"] == "q"

    @pytest.mark.asyncio
    async def test_complete_review_no_review_noop(self, session_maker, test_user):
        """Если нет активного review, complete_review ничего не делает."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            # Не должно упасть
            await svc.complete_review(s, card, True)
            assert card.status == CardStatus.MASTERED  # не изменился

    @pytest.mark.asyncio
    async def test_interval_progression_caps_at_90(self, session_maker, test_user):
        """Интервалы не уходят за максимальный (90 дней)."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            # Создаём review с интервалом 90 (максимальный)
            review = Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1),
                           interval_days=90)
            s.add(review)
            await s.commit()
            card_loaded = await s.get(Card, card.id)
            await svc.complete_review(s, card_loaded, True)

        async with session_maker() as s:
            nxt = await s.scalar(select(Review).where(Review.card_id == card.id, Review.completed_at.is_(None)))
            assert nxt is not None
            assert nxt.interval_days == 90  # cap — не превышает максимум

    @pytest.mark.asyncio
    async def test_get_or_create_session_closes_old_session(self, session_maker, test_user):
        """Сессия старше 4 часов закрывается, создаётся новая."""
        async with session_maker() as s:
            old = LearningSession(user_id=test_user.id, started_at=datetime.utcnow() - timedelta(hours=5))
            s.add(old)
            await s.commit()

        async with session_maker() as s:
            session = await svc.get_or_create_session(s, test_user.id)
            assert session.id != old.id
            # Проверяем, что старая закрыта
            old_loaded = await s.get(LearningSession, old.id)
            assert old_loaded.ended_at is not None

    @pytest.mark.asyncio
    async def test_get_current_card_skips_drafts(self, session_maker, test_user):
        """Draft-карточки не участвуют в обучении."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            draft = Card(topic_id=topic.id, type=CardType.TERM, front_content="d", back_content="d",
                        status=CardStatus.DRAFT, source=CardSource.MCP, order_index=1)
            s.add(draft)
            await s.commit()
            assert await svc.get_current_card(s, topic.id) is None

    @pytest.mark.asyncio
    async def test_generate_write_command(self, session_maker, test_user):
        """Генерация упражнения write_command для COMMAND-карточки."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.COMMAND, front_content="deploy",
                        back_content="kubectl apply -f deploy.yaml",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "write_command")
            assert ex["kind"] == "write_command"
            assert ex["payload"]["prompt"] == "deploy"

    @pytest.mark.asyncio
    async def test_generate_find_bug(self, session_maker, test_user):
        """Генерация упражнения find_bug для COMMAND-карточки."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.COMMAND, front_content="deploy",
                        back_content="kubectl apply -f deploy.yaml",
                        status=CardStatus.LEARNING, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.commit()
            ex = await svc.generate_exercise(s, card, "find_bug")
            assert ex["kind"] == "find_bug"
            assert "ошибку" in ex["payload"]["prompt"]

    @pytest.mark.asyncio
    async def test_complete_review_custom_interval(self, session_maker, test_user):
        """Если interval_days не из стандартного списка, следующее значение берётся из начала."""
        async with session_maker() as s:
            topic = Topic(user_id=test_user.id, name="Test")
            s.add(topic)
            await s.flush()
            card = Card(topic_id=topic.id, type=CardType.TERM, front_content="a", back_content="b",
                        status=CardStatus.MASTERED, source=CardSource.MANUAL, order_index=1)
            s.add(card)
            await s.flush()
            # Нестандартный интервал (нет в REVIEW_INTERVALS)
            review = Review(card_id=card.id, scheduled_at=datetime.utcnow() - timedelta(hours=1),
                           interval_days=5)
            s.add(review)
            await s.commit()
            card_loaded = await s.get(Card, card.id)
            await svc.complete_review(s, card_loaded, True)

        async with session_maker() as s:
            nxt = await s.scalar(select(Review).where(Review.card_id == card.id, Review.completed_at.is_(None)))
            assert nxt is not None
            assert nxt.interval_days == 1  # упало на дефолт — первый элемент списка
