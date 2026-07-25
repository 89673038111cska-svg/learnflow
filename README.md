# LearnFlow

Stepwise learning app for technical knowledge — strict card sequencing, spaced repetition, MCP integration.

## Quick Start

```bash
cp .env.example .env   # заполнить SECRET_KEY, MCP_API_TOKEN, LEARNFLOW_USER_PASSWORD
docker compose up -d

# Backend API: http://localhost:8000 (docs: /docs)
# Frontend: http://localhost:5173
# Логин: $LEARNFLOW_USER_LOGIN / $LEARNFLOW_USER_PASSWORD
```

При старте backend автоматически применяет Alembic-миграции и создаёт seed-пользователя (идемпотентно).

### Переменные окружения (.env)

| Var | Назначение |
|---|---|
| `SECRET_KEY` | Подпись JWT (обязательно сменить вне dev) |
| `MCP_API_TOKEN` | Токен агентов для MCP-сервера |
| `LEARNFLOW_USER_LOGIN` / `LEARNFLOW_USER_PASSWORD` | Seed-пользователь (регистрации нет) |

## Тесты

```bash
cd backend
.venv/bin/python -m pytest tests/ -q    # 41 тест: механика, повторы, MCP, CRUD, auth, контракт
```

Тесты используют отдельную БД `learnflow_test` на том же PostgreSQL (нужен `docker compose up postgres`).

## MCP-сервер (для агентов)

```bash
cd backend
LEARNFLOW_MCP_TOKEN=$MCP_API_TOKEN .venv/bin/python -m app.mcp.server
```

Tools: `add_card_draft`, `list_topics`, `get_learning_status`. Карточки агентов попадают в черновики — учатся только после approve в UI.

## Project Structure

```
learnflow/
├── backend/           # Python + FastAPI
│   ├── app/
│   │   ├── api/       # HTTP endpoints
│   │   ├── core/      # Config, security, database
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── mcp/       # MCP server tools
│   ├── tests/
│   └── requirements.txt
├── frontend/          # React + Vite + TypeScript
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── api/
│   │   └── types/
│   └── package.json
├── docker-compose.yml
└── docs/
```

## Features

- **Strict sequencing**: Learn one card at a time, next unlocks only after mastery
- **Objective mastery**: 3× consecutive correct answers, first attempt, no hints, different sessions
- **Spaced repetition**: 1d → 3d → 7d → 14d intervals, failed reviews return to learning
- **Three card types**: Terms, Commands, Procedures — each with tailored exercises
- **MCP Server**: AI agents can add card drafts for approval
- **AI Generation**: Convert text/notes to card drafts (v1.1)

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS
- **Auth**: JWT (web) + API tokens (MCP)
- **MCP**: Python MCP SDK
- **Deployment**: Docker Compose

## Documentation

- [MVP Spec](https://github.com/89673038111cska-svg/learnflow/issues/1)
