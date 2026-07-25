"""Единый формат ошибок API: {"detail": str, "code": str}.

AppError поднимается в роутерах/сервисах, handler сериализует в ErrorResponse.
HTTPException от FastAPI (404 на уровне роутинга и т.п.) тоже приводится к формату.
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status_code: int, code: str, detail: str):
        self.status_code = status_code
        self.code = code
        self.detail = detail


def _error_body(detail: str, code: str) -> dict:
    return {"detail": detail, "code": code}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.detail, exc.code),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
        }.get(exc.status_code, "http_error")
        detail = exc.detail if isinstance(exc.detail, str) else code
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(detail, code),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body",))
        msg = first.get("msg", "Validation error")
        detail = f"{loc}: {msg}" if loc else msg
        return JSONResponse(
            status_code=422,
            content=_error_body(detail, "validation_error"),
        )
