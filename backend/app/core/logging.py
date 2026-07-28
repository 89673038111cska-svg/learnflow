"""Структурированное логирование (issue #12).

JSON-логи в stdout для docker logs. Уровень через env LOG_LEVEL.
Секреты (пароли, токены) маскируются.
"""
import logging
import os
import re
import sys

import structlog

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Маскировка секретов в логах
_SECRET_PATTERNS = [
    (re.compile(r"password[\"']?\s*[:=]\s*[\"'][^\"']+[\"']", re.I), "password=***"),
    (re.compile(r"token[\"']?\s*[:=]\s*[\"'][^\"']+[\"']", re.I), "token=***"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"), "Bearer ***"),
]


def _mask_secrets(logger, method_name, event_dict):
    """Процессор structlog: маскирует секреты в event и message."""
    for key in ("event", "message"):
        if key in event_dict:
            val = str(event_dict[key])
            for pattern, replacement in _SECRET_PATTERNS:
                val = pattern.sub(replacement, val)
            event_dict[key] = val
    return event_dict


def setup_logging() -> None:
    """Инициализация structlog + stdlib logging в stdout."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=LOG_LEVEL,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _mask_secrets,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
