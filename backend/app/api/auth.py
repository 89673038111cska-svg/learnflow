"""POST /api/auth/login → JWT. Логика — в issue #4, сейчас 501."""
from fastapi import APIRouter

from app.core.errors import AppError
from app.schemas.schemas import ErrorResponse, LoginRequest, TokenResponse, UserResponse

router = APIRouter()

NOT_IMPLEMENTED = AppError(501, "not_implemented", "Auth будет реализован в issue #4")


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 501: {"model": ErrorResponse}},
)
async def login(_: LoginRequest):
    raise NOT_IMPLEMENTED


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}, 501: {"model": ErrorResponse}},
)
async def get_me():
    raise NOT_IMPLEMENTED
