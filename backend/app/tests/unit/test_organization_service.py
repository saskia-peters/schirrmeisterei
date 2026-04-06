import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Organization, OrganizationLevel
from app.services.organization_service import OrganizationService


@pytest_asyncio.fixture
async def svc(db: AsyncSession) -> OrganizationService:
    return OrganizationService(db)


@pytest_asyncio.fixture
async def leitung(db: AsyncSession, svc: OrganizationService) -> Organization:
    org = Organization(level=OrganizationLevel.LEITUNG, name="Bundesleitung", parent_id=None)
    db.add(org)
    await db.flush()
    return org


@pytest_asyncio.fixture
async def landesverband(db: AsyncSession, leitung: Organization) -> Organization:
    org = Organization(
        level=OrganizationLevel.LANDESVERBAND,
        name="LV Bayern",
        parent_id=leitung.id,
    )
    db.add(org)
    await db.flush()
    return org


@pytest_asyncio.fixture
async def regionalstelle(db: AsyncSession, landesverband: Organization) -> Organization:
    org = Organization(
        level=OrganizationLevel.REGIONALSTELLE,
        name="Rst München",
        parent_id=landesverband.id,
    )
    db.add(org)
    await db.flush()
    return org


@pytest_asyncio.fixture
async def ortsverband(db: AsyncSession, regionalstelle: Organization) -> Organization:
    org = Organization(
        level=OrganizationLevel.ORTSVERBAND,
        name="OV Schwabing",
        parent_id=regionalstelle.id,
    )
    db.add(org)
    await db.flush()
    return org


class TestListAll:
    @pytest.mark.asyncio
    async def test_empty(self, svc: OrganizationService) -> None:
        result = await svc.list_all()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_all_orgs(
        self,
        svc: OrganizationService,
        leitung: Organization,
        landesverband: Organization,
    ) -> None:
        result = await svc.list_all()
        ids = [o.id for o in result]
        assert leitung.id in ids
        assert landesverband.id in ids


class TestFindByNameLevel:
    @pytest.mark.asyncio
    async def test_finds_existing(
        self, svc: OrganizationService, landesverband: Organization
    ) -> None:
        found = await svc.find_by_name_level("LV Bayern", OrganizationLevel.LANDESVERBAND)
        assert found is not None
        assert found.id == landesverband.id

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_level(
        self, svc: OrganizationService, landesverband: Organization
    ) -> None:
        found = await svc.find_by_name_level("LV Bayern", OrganizationLevel.ORTSVERBAND)
        assert found is None

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_name(
        self, svc: OrganizationService, landesverband: Organization
    ) -> None:
        found = await svc.find_by_name_level("Does not exist", OrganizationLevel.LANDESVERBAND)
        assert found is None


class TestCreateOrg:
    @pytest.mark.asyncio
    async def test_creates_org(self, svc: OrganizationService) -> None:
        org = await svc.create_org(OrganizationLevel.LEITUNG, "Testleitung", None)
        assert org.id is not None
        assert org.name == "Testleitung"
        assert org.level == OrganizationLevel.LEITUNG
        assert org.parent_id is None

    @pytest.mark.asyncio
    async def test_creates_child_org(
        self, svc: OrganizationService, leitung: Organization
    ) -> None:
        child = await svc.create_org(OrganizationLevel.LANDESVERBAND, "LV Test", leitung.id)
        assert child.parent_id == leitung.id


class TestGetDescendants:
    @pytest.mark.asyncio
    async def test_includes_self_and_children(
        self,
        svc: OrganizationService,
        landesverband: Organization,
        regionalstelle: Organization,
        ortsverband: Organization,
    ) -> None:
        ids = await svc.get_descendants(landesverband.id)
        assert landesverband.id in ids
        assert regionalstelle.id in ids
        assert ortsverband.id in ids

    @pytest.mark.asyncio
    async def test_leaf_node_returns_only_self(
        self, svc: OrganizationService, ortsverband: Organization
    ) -> None:
        ids = await svc.get_descendants(ortsverband.id)
        assert ids == [ortsverband.id]


class TestGetVisibleOrgIds:
    @pytest.mark.asyncio
    async def test_none_org_id_returns_none(self, svc: OrganizationService) -> None:
        result = await svc.get_visible_org_ids(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_leitung_returns_none(
        self, svc: OrganizationService, leitung: Organization
    ) -> None:
        result = await svc.get_visible_org_ids(leitung.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_landesverband_returns_descendants(
        self,
        svc: OrganizationService,
        landesverband: Organization,
        regionalstelle: Organization,
        ortsverband: Organization,
    ) -> None:
        result = await svc.get_visible_org_ids(landesverband.id)
        assert result is not None
        assert landesverband.id in result
        assert regionalstelle.id in result
        assert ortsverband.id in result

    @pytest.mark.asyncio
    async def test_ortsverband_returns_only_self(
        self, svc: OrganizationService, ortsverband: Organization
    ) -> None:
        result = await svc.get_visible_org_ids(ortsverband.id)
        assert result == [ortsverband.id]
