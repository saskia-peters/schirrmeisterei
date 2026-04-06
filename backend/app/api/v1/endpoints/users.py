import os
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_superuser, get_current_user, get_unrestricted_user
from app.core.exceptions import ConflictException, NotFoundException
from app.db.session import get_db
from app.models.models import User
from app.schemas.user import AssignableUserResponse, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/assignable", response_model=list[AssignableUserResponse])
async def list_assignable_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[User]:
    """Return all users as lightweight records for use in assignee selectors."""
    service = UserService(db)
    return await service.list_all()


@router.get("/", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> list[User]:
    """Return all user accounts. Accessible to superusers only."""
    service = UserService(db)
    return await service.list_all()


@router.post("/", response_model=UserResponse)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> User:
    """Create a new user account. Returns 409 if the email is already registered."""
    service = UserService(db)
    existing = await service.get_by_email(data.email)
    if existing:
        raise ConflictException("Email already registered")
    return await service.create(data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> User:
    """Fetch a user by UUID, raising 404 if not found."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise NotFoundException("User")
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_unrestricted_user),
) -> User:
    """Update a user's profile. Users may only update their own record; superusers may update any."""
    if user_id != current_user.id and not current_user.is_superuser:
        from app.core.exceptions import ForbiddenException
        raise ForbiddenException()
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user:
        raise NotFoundException("User")
    return await service.update(user, data)


_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_unrestricted_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Upload a new avatar image for the currently authenticated user.

    Accepts JPEG, PNG, WebP or GIF images up to 2 MB.  The stored file is
    served at ``/uploads/avatars/<user_id>.<ext>`` and the URL is written to
    ``user.avatar_url``.
    """
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, WebP or GIF images are allowed",
        )
    content = await file.read()
    if len(content) > _MAX_AVATAR_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image must be under 2 MB",
        )
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    avatar_dir = Path(settings.UPLOAD_DIR) / "avatars"
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{current_user.id}{ext}"
    filepath = avatar_dir / filename
    # CR-S1: use aiofiles so the async event loop is never blocked
    async with aiofiles.open(filepath, "wb") as fh:
        await fh.write(content)
    current_user.avatar_url = f"/uploads/avatars/{filename}"
    await db.flush()
    service = UserService(db)
    refreshed = await service.get_by_id(current_user.id)
    if refreshed is None:
        raise RuntimeError(f"User {current_user.id} disappeared after avatar upload")
    return refreshed


@router.delete("/me/avatar", response_model=UserResponse)
async def delete_avatar(
    current_user: User = Depends(get_unrestricted_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Remove the current user's avatar image."""
    if current_user.avatar_url:
        # CR-S2: extract only the filename – Path.name strips any directory
        # components, making path-traversal via a crafted avatar_url impossible.
        safe_name = Path(current_user.avatar_url).name
        filepath = Path(settings.UPLOAD_DIR, "avatars", safe_name).resolve()
        upload_root = Path(settings.UPLOAD_DIR).resolve()
        if filepath.is_relative_to(upload_root):
            try:
                filepath.unlink(missing_ok=True)
            except OSError:
                pass
    current_user.avatar_url = None
    await db.flush()
    service = UserService(db)
    refreshed = await service.get_by_id(current_user.id)
    if refreshed is None:
        raise RuntimeError(f"User {current_user.id} disappeared after avatar deletion")
    return refreshed
