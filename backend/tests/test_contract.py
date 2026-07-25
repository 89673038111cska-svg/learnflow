"""Тесты API-контракта (issue #2).

Проверяют, что все endpoints MVP присутствуют в OpenAPI,
схемы ошибок соответствуют единому формату, а ответы
роутеров валидируются заявленными response_model.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_PATHS = {
    "/api/auth/login": ["post"],
    "/api/auth/me": ["get"],
    "/api/topics": ["get", "post"],
    "/api/topics/{topic_id}": ["get", "patch", "delete"],
    "/api/topics/{topic_id}/cards": ["get"],
    "/api/cards": ["post"],
    "/api/cards/drafts": ["get"],
    "/api/cards/{card_id}": ["patch", "delete"],
    "/api/cards/{card_id}/approve": ["post"],
    "/api/cards/{card_id}/reject": ["post"],
    "/api/learning/state": ["get"],
    "/api/learning/attempt": ["post"],
    "/api/reviews/due": ["get"],
    "/api/reviews/{review_id}/complete": ["post"],
}

CORE_SCHEMAS = [
    "TokenResponse",
    "UserResponse",
    "TopicCreate",
    "TopicUpdate",
    "TopicResponse",
    "CardCreate",
    "CardUpdate",
    "CardResponse",
    "DraftActionResponse",
    "Exercise",
    "ExerciseAttempt",
    "AttemptResult",
    "LearningStateResponse",
    "ReviewResponse",
    "ReviewCompleteRequest",
    "ReviewCompleteResponse",
    "ErrorResponse",
    "CardType",
    "CardStatus",
    "CardSource",
]


@pytest.fixture(scope="module")
def openapi_spec():
    return client.get("/openapi.json").json()


def test_all_endpoints_present(openapi_spec):
    paths = openapi_spec["paths"]
    for path, methods in EXPECTED_PATHS.items():
        assert path in paths, f"Missing path: {path}"
        for method in methods:
            assert method in paths[path], f"Missing {method.upper()} {path}"


def test_core_schemas_present(openapi_spec):
    schemas = openapi_spec["components"]["schemas"]
    for name in CORE_SCHEMAS:
        assert name in schemas, f"Missing schema: {name}"


def test_error_response_format():
    """Единый формат ошибок: {"detail": str, "code": str}."""
    # 501 от заглушки
    resp = client.get("/api/topics")
    assert resp.status_code == 501
    body = resp.json()
    assert set(body.keys()) == {"detail", "code"}
    assert body["code"] == "not_implemented"

    # 404 на несуществующий роут
    resp = client.get("/api/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) == {"detail", "code"}
    assert body["code"] == "not_found"


def test_validation_error_format():
    """422 тоже в едином формате, без FastAPI-вложенности."""
    resp = client.post("/api/topics", json={"description": "no name field"})
    assert resp.status_code == 422
    body = resp.json()
    assert set(body.keys()) == {"detail", "code"}
    assert body["code"] == "validation_error"


def test_exported_spec_matches_live(openapi_spec):
    """docs/openapi.json соответствует живой схеме (не протух).

    Если падает — запусти scripts/export_openapi.py и регенерируй TS-типы.
    """
    exported = Path(__file__).parent.parent.parent / "docs" / "openapi.json"
    assert exported.exists(), "docs/openapi.json не существует — запусти export"
    saved = json.loads(exported.read_text())
    assert saved == openapi_spec, (
        "docs/openapi.json устарел: запусти "
        "backend/.venv/bin/python backend/scripts/export_openapi.py"
    )
