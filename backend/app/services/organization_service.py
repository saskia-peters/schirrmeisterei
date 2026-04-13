from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Organization, OrganizationLevel


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a database session."""
        self.db = db

    async def get_by_id(self, org_id: str) -> Organization | None:
        """Fetch a single Organisation by its UUID, or None if not found."""
        result = await self.db.execute(
            select(Organization)
            .options(selectinload(Organization.children))
            .where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Organization]:
        """Return all organisations ordered by level then name."""
        result = await self.db.execute(
            select(Organization).order_by(Organization.level, Organization.name)
        )
        return list(result.scalars().all())

    async def list_by_level(self, level: OrganizationLevel) -> list[Organization]:
        """Return all organisations matching the given hierarchy level."""
        result = await self.db.execute(
            select(Organization)
            .where(Organization.level == level)
            .order_by(Organization.name)
        )
        return list(result.scalars().all())

    async def list_children(self, parent_id: str) -> list[Organization]:
        """Return the direct children of the organisation identified by parent_id."""
        result = await self.db.execute(
            select(Organization)
            .where(Organization.parent_id == parent_id)
            .order_by(Organization.name)
        )
        return list(result.scalars().all())

    async def get_descendants(self, org_id: str) -> list[str]:
        """Return all descendant org IDs (including the given org_id).

        Current implementation: BFS with one SELECT per level -- acceptable at
        ≤10 org nodes.  SCALE-UP (P-2): replace with a single PostgreSQL
        recursive CTE when the org hierarchy grows or query latency increases.
        See SCALING.md § Organisation Hierarchy and REVIEW.md P-2.
        """
        ids: list[str] = [org_id]
        queue = [org_id]
        while queue:
            current = queue.pop(0)
            children = await self.list_children(current)
            for child in children:
                ids.append(child.id)
                queue.append(child.id)
        return ids

    async def get_visible_org_ids(self, user_org_id: str | None) -> list[str] | None:
        """Return the list of organization IDs a user can see, based on their org.

        - Superadmins (org_id=None) see everything → returns None (no filter).
        - Leitung level → all orgs (returns None).
        - Any other level → the org itself plus all descendants.
        """
        if user_org_id is None:
            return None  # no filter
        org = await self.get_by_id(user_org_id)
        if org is None:
            return [user_org_id]
        if org.level == OrganizationLevel.LEITUNG:
            return None  # sees everything
        return await self.get_descendants(user_org_id)

    async def list_landesverbaende(self) -> list[Organization]:
        """Return all Landesverbände."""
        return await self.list_by_level(OrganizationLevel.LANDESVERBAND)

    async def list_regionalstellen(self, landesverband_id: str | None = None) -> list[Organization]:
        """Return all Regionalstellen, optionally filtered by their parent Landesverband."""
        stmt = select(Organization).where(
            Organization.level == OrganizationLevel.REGIONALSTELLE
        )
        if landesverband_id:
            stmt = stmt.where(Organization.parent_id == landesverband_id)
        result = await self.db.execute(stmt.order_by(Organization.name))
        return list(result.scalars().all())

    async def list_ortserbaende(self, regionalstelle_id: str | None = None) -> list[Organization]:
        """Return all Ortsverbände, optionally filtered by their parent Regionalstelle."""
        stmt = select(Organization).where(
            Organization.level == OrganizationLevel.ORTSVERBAND
        )
        if regionalstelle_id:
            stmt = stmt.where(Organization.parent_id == regionalstelle_id)
        result = await self.db.execute(stmt.order_by(Organization.name))
        return list(result.scalars().all())

    async def find_by_name_level(self, name: str, level: OrganizationLevel) -> Organization | None:
        """Find a single organisation by exact name and level, or None if not found."""
        result = await self.db.execute(
            select(Organization)
            .where(Organization.name == name, Organization.level == level)
        )
        return result.scalar_one_or_none()

    async def create_org(
        self, level: OrganizationLevel, name: str, parent_id: str | None
    ) -> Organization:
        """Create and persist a new Organisation node."""
        org = Organization(level=level, name=name, parent_id=parent_id)
        self.db.add(org)
        await self.db.flush()
        return org
