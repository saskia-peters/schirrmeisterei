from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.models import User
from app.services.user_service import UserService

bearer_scheme = HTTPBearer()


async def _get_user_base(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer token and confirm the account is active.

    Does NOT enforce force_password_change so it can be reused by
    GET /auth/me and PATCH /users/{id}, which must stay accessible
    during the forced-password-change flow.
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


# Alias for the two endpoints that must work while force_password_change is True.
get_unrestricted_user = _get_user_base


async def get_current_user(
    user: User = Depends(_get_user_base),
) -> User:
    """Like _get_user_base but additionally blocks accounts that still
    require a forced password change from accessing standard endpoints."""
    if user.force_password_change:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PASSWORD_CHANGE_REQUIRED",
        )
    return user


async def get_admin_group_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow access only to users in the 'admin' group or superusers."""
    if current_user.is_superuser or any(g.name == "admin" for g in current_user.groups):
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions",
    )


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Allow access only to superusers; raises 403 for all others."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
