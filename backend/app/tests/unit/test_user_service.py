import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Organization, OrganizationLevel, User, UserGroup
from app.schemas.user import UserCreate
from app.services.user_service import UserService


@pytest_asyncio.fixture
async def svc(db: AsyncSession) -> UserService:
    return UserService(db)


class TestEnsureCoreGroups:
    @pytest.mark.asyncio
    async def test_creates_core_groups(self, svc: UserService, db: AsyncSession) -> None:
        await svc.ensure_core_groups()
        groups = await svc.list_groups()
        names = {g.name for g in groups}
        assert "helfende" in names
        assert "schirrmeister" in names
        assert "admin" in names

    @pytest.mark.asyncio
    async def test_idempotent(self, svc: UserService) -> None:
        await svc.ensure_core_groups()
        await svc.ensure_core_groups()  # second call should not raise
        groups = await svc.list_groups()
        assert len(groups) == 3


class TestCreate:
    @pytest.mark.asyncio
    async def test_creates_user(self, svc: UserService) -> None:
        data = UserCreate(
            email="alice@example.com",
            full_name="Alice",
            password="password123",
        )
        user = await svc.create(data)
        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.full_name == "Alice"

    @pytest.mark.asyncio
    async def test_password_is_hashed(self, svc: UserService) -> None:
        data = UserCreate(email="bob@example.com", full_name="Bob", password="secret12")
        user = await svc.create(data)
        assert user.hashed_password != "secret"

    @pytest.mark.asyncio
    async def test_new_user_has_helfende_group(self, svc: UserService) -> None:
        data = UserCreate(email="carol@example.com", full_name="Carol", password="secret12")
        user = await svc.create(data)
        group_names = {g.name for g in user.groups}
        assert "helfende" in group_names

    @pytest.mark.asyncio
    async def test_user_with_organization(
        self, svc: UserService, db: AsyncSession
    ) -> None:
        org = Organization(
            level=OrganizationLevel.ORTSVERBAND, name="OV Test", parent_id=None
        )
        db.add(org)
        await db.flush()
        data = UserCreate(
            email="dave@example.com",
            full_name="Dave",
            password="secret12",
            organization_id=org.id,
        )
        user = await svc.create(data)
        assert user.organization_id == org.id


class TestGetByEmail:
    @pytest.mark.asyncio
    async def test_finds_existing_user(self, svc: UserService) -> None:
        data = UserCreate(email="eve@example.com", full_name="Eve", password="password1")
        created = await svc.create(data)
        found = await svc.get_by_email("eve@example.com")
        assert found is not None
        assert found.id == created.id

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self, svc: UserService) -> None:
        result = await svc.get_by_email("nobody@example.com")
        assert result is None


class TestAuthenticate:
    @pytest.mark.asyncio
    async def test_valid_credentials(self, svc: UserService) -> None:
        await svc.create(
            UserCreate(email="frank@example.com", full_name="Frank", password="correctXX")
        )
        user = await svc.authenticate("frank@example.com", "correctXX")
        assert user is not None
        assert user.email == "frank@example.com"

    @pytest.mark.asyncio
    async def test_wrong_password(self, svc: UserService) -> None:
        await svc.create(
            UserCreate(email="grace@example.com", full_name="Grace", password="correctXX")
        )
        user = await svc.authenticate("grace@example.com", "wrong")
        assert user is None

    @pytest.mark.asyncio
    async def test_unknown_email(self, svc: UserService) -> None:
        user = await svc.authenticate("noone@example.com", "anything")
        assert user is None


class TestAssignGroups:
    @pytest.mark.asyncio
    async def test_assigns_additional_group(self, svc: UserService, db: AsyncSession) -> None:
        user = await svc.create(
            UserCreate(email="heidi@example.com", full_name="Heidi", password="password1")
        )
        await svc.assign_groups(user, {"schirrmeister"})
        # Verify via direct DB query to bypass ORM identity-map caching
        from sqlalchemy import select as sa_select
        from app.models.models import UserGroupMembership as UGM, UserGroup as UG
        result = await db.execute(
            sa_select(UG.name)
            .join(UGM, UG.id == UGM.group_id)
            .where(UGM.user_id == user.id)
        )
        names = {row[0] for row in result.all()}
        assert "helfende" in names
        assert "schirrmeister" in names

    @pytest.mark.asyncio
    async def test_raises_for_unknown_group(
        self, svc: UserService, db: AsyncSession
    ) -> None:
        user = await svc.create(
            UserCreate(email="ivan@example.com", full_name="Ivan", password="password1")
        )
        with pytest.raises(ValueError, match="Unknown groups"):
            await svc.assign_groups(user, {"nonexistent_group"})
