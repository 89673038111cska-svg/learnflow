"""Shared fixtures: тестовая БД, клиент, пользователь.

PostgreSQL из docker-compose (порт 5432), отдельная БД learnflow_test.
NullPool — каждый запрос новое соединение, избегаем event loop конфликтов.
"""
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models.models import User

TEST_DB_URL = settings.DATABASE_URL.rsplit("/learnflow", 1)[0] + "/learnflow_test"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def test_user(session_maker):
    """Создаёт тестового пользователя ДО клиента."""
    async with session_maker() as session:
        user = User(login="testuser", password_hash=get_password_hash("testpass123"))
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def client(session_maker, test_user):
    """HTTP-клиент с переопределённой БД. Зависит от test_user — пользователь уже есть."""
    async def override_get_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_token(client):
    resp = await client.post(
        "/api/auth/login", json={"login": "testuser", "password": "testpass123"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}
