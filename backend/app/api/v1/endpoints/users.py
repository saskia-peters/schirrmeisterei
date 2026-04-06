from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

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
