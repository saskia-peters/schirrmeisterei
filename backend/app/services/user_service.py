from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_password_hash, verify_password
from app.models.models import User, UserGroup, UserGroupMembership, UserGroupName
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a database session."""
        self.db = db

    def _user_options(self) -> list:
        """Return the standard eager-load options used when fetching User objects."""
        return [selectinload(User.groups).selectinload(UserGroup.permissions), selectinload(User.organization)]

    async def get_by_id(self, user_id: str) -> User | None:
        """Fetch a User by their UUID, with groups/permissions and organisation eager-loaded."""
        result = await self.db.execute(
            select(User).options(*self._user_options()).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a User by their email address, or None if not found."""
        result = await self.db.execute(
            select(User).options(*self._user_options()).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def ensure_core_groups(self) -> None:
        """Create the helfende, schirrmeister and admin groups if they do not already exist."""
        existing = await self.db.execute(select(UserGroup.name))
        names = {row[0] for row in existing.all()}
        for name in (
            UserGroupName.HELFENDE.value,
            UserGroupName.SCHIRRMEISTER.value,
            UserGroupName.ADMIN.value,
        ):
            if name not in names:
                self.db.add(UserGroup(name=name))
        await self.db.flush()

    async def get_group_by_name(self, name: str) -> UserGroup | None:
        """Look up a UserGroup by exact name, or return None if it doesn't exist."""
        result = await self.db.execute(select(UserGroup).where(UserGroup.name == name))
        return result.scalar_one_or_none()

    async def list_groups(self) -> list[UserGroup]:
        """Return all UserGroups ordered by name."""
        result = await self.db.execute(select(UserGroup).order_by(UserGroup.name))
        return list(result.scalars().all())

    async def create_group(self, name: str) -> UserGroup:
        """Create and persist a new UserGroup with the given name."""
        group = UserGroup(name=name)
        self.db.add(group)
        await self.db.flush()
        await self.db.refresh(group)
        return group

    async def assign_groups(self, user: User, group_names: set[str]) -> User:
        """Replace the user's group memberships with the given set of group names.

        The helfende group is always included.  Raises ValueError if any name
        is not a known group.
        """
        await self.ensure_core_groups()
        normalized = {name.strip().lower() for name in group_names if name.strip()}
        normalized.add(UserGroupName.HELFENDE.value)

        groups_result = await self.db.execute(select(UserGroup).where(UserGroup.name.in_(normalized)))
        groups = list(groups_result.scalars().all())
        found_names = {g.name for g in groups}
        missing = normalized - found_names
        if missing:
            raise ValueError(f"Unknown groups: {', '.join(sorted(missing))}")

        await self.db.execute(
            delete(UserGroupMembership).where(UserGroupMembership.user_id == user.id)
        )
        for group in groups:
            self.db.add(UserGroupMembership(user_id=user.id, group_id=group.id))
        await self.db.flush()
        refreshed = await self.get_by_id(user.id)
        assert refreshed is not None
        return refreshed

    async def user_has_any_group(self, user_id: str, names: set[str]) -> bool:
        """Return True if the user belongs to at least one of the given group names."""
        normalized = {name.strip().lower() for name in names}
        stmt = (
            select(UserGroupMembership)
            .join(UserGroup, UserGroupMembership.group_id == UserGroup.id)
            .where(UserGroupMembership.user_id == user_id, UserGroup.name.in_(normalized))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create(self, data: UserCreate) -> User:
        """Create a new User from the supplied UserCreate schema and add them to the helfende group."""
        await self.ensure_core_groups()
        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=get_password_hash(data.password),
            organization_id=data.organization_id,
        )
        self.db.add(user)
        await self.db.flush()
        helfende = await self.get_group_by_name(UserGroupName.HELFENDE.value)
        assert helfende is not None
        self.db.add(UserGroupMembership(user_id=user.id, group_id=helfende.id))
        await self.db.flush()
        refreshed = await self.get_by_id(user.id)
        assert refreshed is not None
        return refreshed

    async def update(self, user: User, data: UserUpdate) -> User:
        """Apply UserUpdate fields to the user record and flush to the database."""
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.password is not None:
            user.hashed_password = get_password_hash(data.password)
            user.force_password_change = False
        await self.db.flush()
        refreshed = await self.get_by_id(user.id)
        assert refreshed is not None
        return refreshed

    async def authenticate(self, email: str, password: str) -> User | None:
        """Verify email/password credentials. Returns the User on success, None on failure."""
        user = await self.get_by_email(email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def set_totp_secret(self, user: User, secret: str) -> User:
        """Persist a newly generated TOTP secret on the user (TOTP not yet enabled)."""
        user.totp_secret = secret
        await self.db.flush()
        return user

    async def enable_totp(self, user: User) -> User:
        """Mark TOTP as enabled after the user has successfully verified their first code."""
        user.totp_enabled = True
        await self.db.flush()
        return user

    async def disable_totp(self, user: User) -> User:
        """Disable TOTP for the user and clear the stored secret."""
        user.totp_enabled = False
        user.totp_secret = None
        await self.db.flush()
        return user

    async def list_all(self) -> list[User]:
        """Return all users with groups/permissions and organisation eager-loaded."""
        result = await self.db.execute(select(User).options(*self._user_options()))
        return list(result.scalars().all())

    async def user_has_permission(self, user_id: str, permission_codename: str) -> bool:
        """Check if a user has a specific permission via any of their groups."""
        user = await self.get_by_id(user_id)
        if user is None:
            return False
        if user.is_superuser:
            return True
        for group in user.groups:
            if any(p.codename == permission_codename for p in group.permissions):
                return True
        return False
