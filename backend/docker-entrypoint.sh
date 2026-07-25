#!/bin/sh
# Entrypoint backend-контейнера: миграции → seed user → uvicorn.
set -e

echo "[entrypoint] Running alembic migrations..."
alembic upgrade head

echo "[entrypoint] Seeding user (idempotent)..."
python scripts/seed_user.py

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 ${UVICORN_ARGS:-}
