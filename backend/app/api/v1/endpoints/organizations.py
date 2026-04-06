from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.models import OrganizationLevel, User
from app.schemas.user import OrganizationResponse
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/", response_model=list[OrganizationResponse])
async def list_organizations(
    level: str | None = None,
    parent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List organizations. Optionally filter by level or parent_id.
    This endpoint is public (needed for registration dropdowns)."""
    service = OrganizationService(db)
    if parent_id:
        return await service.list_children(parent_id)
    if level:
        try:
            org_level = OrganizationLevel(level)
        except ValueError:
            return []
        return await service.list_by_level(org_level)
    return await service.list_all()


@router.get("/landesverbaende", response_model=list[OrganizationResponse])
async def list_landesverbaende(
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List all Landesverbände (for registration dropdown)."""
    service = OrganizationService(db)
    return await service.list_landesverbaende()


@router.get("/regionalstellen", response_model=list[OrganizationResponse])
async def list_regionalstellen(
    landesverband_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List Regionalstellen, optionally filtered by Landesverband."""
    service = OrganizationService(db)
    return await service.list_regionalstellen(landesverband_id)


@router.get("/ortsverbaende", response_model=list[OrganizationResponse])
async def list_ortsverbaende(
    regionalstelle_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List Ortsverbände, optionally filtered by Regionalstelle."""
    service = OrganizationService(db)
    return await service.list_ortserbaende(regionalstelle_id)
