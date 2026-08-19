# Restore "different sessions" rule in record_attempt

## Why

Коммит 8a5dc16 (issue #16) убрал проверку `different_session` целиком («вариант А»),
потому что счётчик `consecutive_correct` не рос внутри одной 4-часовой сессии.
Побочный эффект: карточку теперь можно «освоить», ответив на одно и то же упражнение
3 раза подряд за минуту — это ломает анти-зубрёжную механику, заявленную в спеке
(issue #1) и README («different sessions»), и противоречит смыслу интервального
обучения. API-тест `test_same_session_correct_does_not_increment` при этом не был
обновлён и падает на main.

## What Changes

- В `record_attempt` возвращается правило: верный ответ без подсказки засчитывается
  (инкрементирует `consecutive_correct`) только если последняя засчитанная попытка
  по этому упражнению была в другой сессии (`last_session_id != session.id`).
- Верный ответ в той же сессии — не засчитывается и не ломает серию (как до 8a5dc16).
- Ошибка или подсказка по-прежнему сбрасывают серию (без изменений).
- Сервисный тест `test_record_attempt_increments_in_same_session` возвращается
  к спечному поведению (в той же сессии счётчик не растёт).
- Известный UX-компромисс: освоение упражнения требует 3 сессий; сессия живёт
  4 часа (`get_or_create_session`), далее открывается новая автоматически.

## Capabilities

### Modified Capabilities
- `learning-attempt`: восстановление правила «разные сессии» при подсчёте серии.

## Impact

- `backend/app/services/learning.py` — `record_attempt` (возврат проверки сессии).
- `backend/tests/test_learning_service.py` — актуализация теста same-session.
- `backend/tests/test_learning.py` — `test_same_session_correct_does_not_increment`
  снова проходит без изменений.
- Без изменений API-контракта и схемы БД.

## Risks

- Пользователи снова не смогут «прокликать» карточку за один вечер — осознанное
  продуктовое решение (требование спеки).
