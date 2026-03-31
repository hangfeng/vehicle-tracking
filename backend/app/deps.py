import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, false
from sqlalchemy.sql import Select
from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import decode_token

bearer = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(payload["sub"]), User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_data_scope(
    user: User = Depends(get_current_user),
    _: AsyncSession = Depends(get_db),
) -> str | list[uuid.UUID]:
    if user.role == UserRole.system_admin:
        return "ALL"

    if user.role == UserRole.group_admin:
        factory_ids = getattr(user, "factory_ids", None)
        if factory_ids is not None:
            return list(factory_ids)
        return "ALL"

    if user.role in (UserRole.factory_manager, UserRole.operator) and user.factory_id is not None:
        return [user.factory_id]

    return []


def apply_data_scope(
    query: Select,
    factory_column,
    scope: str | list[uuid.UUID],
    requested_factory_id: uuid.UUID | None = None,
) -> Select:
    if requested_factory_id is not None:
        query = query.where(factory_column == requested_factory_id)

    if scope == "ALL":
        return query

    if not scope:
        return query.where(false())

    return query.where(factory_column.in_(scope))


def require_roles(*roles: UserRole):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role == UserRole.system_admin:
            return user  # system_admin bypasses all role checks
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker
