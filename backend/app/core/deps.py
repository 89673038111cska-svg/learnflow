"""FastAPI dependencies: JWT-аутентификация."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)

UNAUTHORIZED = AppError(401, "unauthorized", "Not authenticated")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UNAUTHORIZED

    payload = decode_token(credentials.credentials)
    if payload is None:
        raise AppError(401, "invalid_token", "Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise AppError(401, "invalid_token", "Token missing subject")

    user = await db.scalar(select(User).where(User.id == int(user_id)))
    if user is None:
        raise AppError(401, "invalid_token", "User not found")

    return user
