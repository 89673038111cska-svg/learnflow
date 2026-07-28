"""Экспорт OpenAPI-схемы в docs/openapi.json.

Используется для генерации TS-типов и contract-check.
Запуск: backend/.venv/bin/python scripts/export_openapi.py
"""
import json
import sys
from pathlib import Path

# Добавляем корень backend в PYTHONPATH для импорта app
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from fastapi.testclient import TestClient

from app.main import app

OUTPUT = Path(__file__).parent.parent.parent / "docs" / "openapi.json"


def main() -> None:
    client = TestClient(app)
    spec = client.get("/openapi.json").json()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    print(f"OpenAPI schema exported to {OUTPUT}")


if __name__ == "__main__":
    main()
