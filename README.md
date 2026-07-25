# LearnFlow

Stepwise learning app for technical knowledge — strict card sequencing, spaced repetition, MCP integration.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Backend API: http://localhost:8000
# Frontend: http://localhost:5173
# PostgreSQL: localhost:5432
```

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
