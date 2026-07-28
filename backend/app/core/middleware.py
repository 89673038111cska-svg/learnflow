"""HTTP-логирование: метод, path, статус, время обработки."""
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger("http")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # Пропускаем /health — слишком шумно
        if request.url.path == "/health":
            return await call_next(request)

        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        log = logger.bind(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        if response.status_code >= 500:
            log.error("http_request")
        elif response.status_code >= 400:
            log.warning("http_request")
        else:
            log.info("http_request")

        return response
