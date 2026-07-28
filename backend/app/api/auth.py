"""POST /api/auth/login → JWT."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.logging import get_logger
from app.core.security import create_access_token, verify_password
from app.models.models import User
from app.schemas.schemas import ErrorResponse, LoginRequest, TokenResponse, UserResponse

router = APIRouter()
logger = get_logger("auth")

INVALID_CREDENTIALS = AppError(401, "invalid_credentials", "Invalid login or password")


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.login == body.login))
    if user is None or not verify_password(body.password, user.password_hash):
        logger.warning("login_failed", login=body.login)
        raise INVALID_CREDENTIALS

    token = create_access_token({"sub": str(user.id)})
    logger.info("login_success", user_id=user.id, login=user.login)
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    responses={401: {"model": ErrorResponse}},
)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
