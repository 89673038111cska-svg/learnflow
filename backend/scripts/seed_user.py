"""Seed single user (MVP: регистрации нет, пользователь из env).

Идемпотентный: повторный запуск не падает и не дублирует.
Env: LEARNFLOW_USER_LOGIN, LEARNFLOW_USER_PASSWORD.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.models import User


async def main() -> int:
    login = os.getenv("LEARNFLOW_USER_LOGIN", "kirill")
    password = os.getenv("LEARNFLOW_USER_PASSWORD")
    if not password:
        print("[seed] LEARNFLOW_USER_PASSWORD не задан — пропускаю seed", file=sys.stderr)
        return 0

    async with async_session_maker() as session:
        existing = await session.scalar(select(User).where(User.login == login))
        if existing:
            print(f"[seed] User '{login}' уже существует (id={existing.id}) — пропускаю")
            return 0

        user = User(login=login, password_hash=get_password_hash(password))
        session.add(user)
        await session.commit()
        print(f"[seed] Создан пользователь '{login}' (id={user.id})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
