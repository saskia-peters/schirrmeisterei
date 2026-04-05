from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_admin_group_user, get_current_superuser, get_current_user
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.db.session import get_db
from app.models.models import AppSetting, ConfigItem, ConfigItemType, User
from app.schemas.config import ConfigItemCreate, ConfigItemResponse, ConfigItemUpdate
from app.schemas.user import (
    AppSettingResponse,
    AppSettingUpdate,
    UserGroupAssignmentUpdate,
    UserGroupCreate,
    UserGroupResponse,
    UserGroupUpdate,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/config-items", response_model=list[ConfigItemResponse])
async def list_config_items(
    type: ConfigItemType | None = None,
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ConfigItem]:
    stmt = select(ConfigItem)
    if type is not None:
        stmt = stmt.where(ConfigItem.type == type)
    if not include_inactive:
        stmt = stmt.where(ConfigItem.is_active == True)  # noqa: E712
    stmt = stmt.order_by(ConfigItem.type, ConfigItem.sort_order, ConfigItem.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/config-items", response_model=ConfigItemResponse, status_code=201)
async def create_config_item(
    data: ConfigItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> ConfigItem:
    item = ConfigItem(
        type=data.type,
        name=data.name,
        sort_order=data.sort_order,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.patch("/config-items/{item_id}", response_model=ConfigItemResponse)
async def update_config_item(
    item_id: str,
    data: ConfigItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> ConfigItem:
    result = await db.execute(select(ConfigItem).where(ConfigItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundException("ConfigItem")
    if data.name is not None:
        item.name = data.name
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    if data.is_active is not None:
        item.is_active = data.is_active
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/config-items/{item_id}", status_code=204)
async def delete_config_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> None:
    result = await db.execute(select(ConfigItem).where(ConfigItem.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundException("ConfigItem")
    await db.delete(item)
    await db.flush()


@router.get("/user-groups", response_model=list[UserGroupResponse])
async def list_user_groups(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> list[UserGroupResponse]:
    service = UserService(db)
    return await service.list_groups()


@router.post("/user-groups", response_model=UserGroupResponse, status_code=201)
async def create_user_group(
    data: UserGroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> UserGroupResponse:
    service = UserService(db)
    name = data.name.strip().lower()
    if not name:
        raise ValidationException("Group name cannot be empty")
    existing = await service.get_group_by_name(name)
    if existing is not None:
        raise ConflictException("Group already exists")
    return await service.create_group(name)


@router.patch("/user-groups/{group_id}", response_model=UserGroupResponse)
async def rename_user_group(
    group_id: str,
    data: UserGroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> UserGroupResponse:
    service = UserService(db)
    groups = await service.list_groups()
    group = next((g for g in groups if g.id == group_id), None)
    if group is None:
        raise NotFoundException("UserGroup")

    name = data.name.strip().lower()
    if not name:
        raise ValidationException("Group name cannot be empty")
    existing = await service.get_group_by_name(name)
    if existing is not None and existing.id != group.id:
        raise ConflictException("Group already exists")

    if group.name == "helfende" and name != "helfende":
        raise ValidationException("The helfende group cannot be renamed")

    group.name = name
    await db.flush()
    await db.refresh(group)
    return group


@router.delete("/user-groups/{group_id}", status_code=204)
async def delete_user_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> None:
    service = UserService(db)
    groups = await service.list_groups()
    group = next((g for g in groups if g.id == group_id), None)
    if group is None:
        raise NotFoundException("UserGroup")
    if group.name in {"helfende", "schirrmeister", "admin"}:
        raise ValidationException("Core groups cannot be deleted")
    await db.delete(group)
    await db.flush()


@router.get("/users/{user_id}/groups", response_model=list[str])
async def get_user_group_names(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> list[str]:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if user is None:
        raise NotFoundException("User")
    return sorted([group.name for group in user.groups])


@router.put("/users/{user_id}/groups", response_model=list[str])
async def set_user_groups(
    user_id: str,
    data: UserGroupAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> list[str]:
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if user is None:
        raise NotFoundException("User")
    try:
        updated = await service.assign_groups(user, set(data.group_names))
    except ValueError as exc:
        raise ValidationException(str(exc)) from exc
    return sorted([group.name for group in updated.groups])


@router.get("/users", response_model=list[UserResponse])
async def list_users_for_admin(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_group_user),
) -> list[User]:
    """Return all users with their group memberships.
    Accessible to superusers and members of the 'admin' group.
    """
    service = UserService(db)
    return await service.list_all()


# ─── App Settings ──────────────────────────────────────────────────────────────

AGE_THRESHOLD_KEYS = [
    "age_green_days",
    "age_light_green_days",
    "age_yellow_days",
    "age_orange_days",
    "age_light_red_days",
]

AGE_THRESHOLD_DEFAULTS: dict[str, str] = {
    "age_green_days": "3",
    "age_light_green_days": "7",
    "age_yellow_days": "14",
    "age_orange_days": "21",
    "age_light_red_days": "30",
}


async def _ensure_age_defaults(db: AsyncSession) -> None:
    for key, default in AGE_THRESHOLD_DEFAULTS.items():
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        if result.scalar_one_or_none() is None:
            db.add(AppSetting(key=key, value=default))
    await db.flush()


@router.get("/app-settings", response_model=list[AppSettingResponse])
async def list_app_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[AppSetting]:
    await _ensure_age_defaults(db)
    result = await db.execute(select(AppSetting).order_by(AppSetting.key))
    return list(result.scalars().all())


@router.patch("/app-settings/{key}", response_model=AppSettingResponse)
async def update_app_setting(
    key: str,
    data: AppSettingUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superuser),
) -> AppSetting:
    await _ensure_age_defaults(db)
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        raise NotFoundException("AppSetting")
    # For age threshold keys, validate that value is a positive integer
    if key in AGE_THRESHOLD_KEYS:
        try:
            days = int(data.value)
            if days < 1:
                raise ValueError
        except ValueError:
            raise ValidationException(
                "Age threshold must be a positive integer (number of days)"
            ) from None
    setting.value = data.value
    await db.flush()
    await db.refresh(setting)
    return setting
