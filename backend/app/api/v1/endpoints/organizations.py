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
    _: User = Depends(get_current_user),
) -> list[OrganizationResponse]:
    """List organizations with optional level/parent_id filters. Requires authentication (A-2).

    Used by the authenticated admin panel. The registration-specific endpoints
    (/landesverbaende, /regionalstellen, /ortsverbaende) are intentionally public
    because they are called before the user has a token.
    """
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
    """List all Landesverbände.

    Intentionally public: called from the unauthenticated registration form so
    that new users can select their Landesverband before they have a token.
    Only name, level, and ID are exposed — no user or ticket data.
    """
    service = OrganizationService(db)
    return await service.list_landesverbaende()


@router.get("/regionalstellen", response_model=list[OrganizationResponse])
async def list_regionalstellen(
    landesverband_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List Regionalstellen, optionally filtered by Landesverband.

    Intentionally public: called from the unauthenticated registration form.
    """
    service = OrganizationService(db)
    return await service.list_regionalstellen(landesverband_id)


@router.get("/ortsverbaende", response_model=list[OrganizationResponse])
async def list_ortsverbaende(
    regionalstelle_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[OrganizationResponse]:
    """List Ortsverbände, optionally filtered by Regionalstelle.

    Intentionally public: called from the unauthenticated registration form.
    """
    service = OrganizationService(db)
    return await service.list_ortserbaende(regionalstelle_id)
