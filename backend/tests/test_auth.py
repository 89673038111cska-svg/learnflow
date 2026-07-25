"""Тесты аутентификации (issue #4)."""
import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post(
        "/api/auth/login", json={"login": "testuser", "password": "testpass123"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/auth/login", json={"login": "testuser", "password": "wrong"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/auth/login", json={"login": "nobody", "password": "x"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


@pytest.mark.asyncio
async def test_me_without_token(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_me_with_invalid_token(client):
    resp = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer garbage.token.here"}
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_token"


@pytest.mark.asyncio
async def test_me_with_valid_token(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["login"] == "testuser"
