from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.core.config import settings
from app.db.session import get_db
from app.models.models import Attachment, Ticket, TicketStatus, User
from app.schemas.ticket import (
    AttachmentResponse,
    CommentCreate,
    CommentResponse,
    CommentUpdate,
    KanbanBoard,
    StatusLogResponse,
    TicketCreate,
    TicketResponse,
    TicketStatusUpdate,
    TicketSummary,
    TicketUpdate,
    WaitingForUpdate,
)
from app.services.organization_service import OrganizationService
from app.services.ticket_service import TicketService
from app.services.user_service import UserService

router = APIRouter(prefix="/tickets", tags=["tickets"])


async def _get_visible_org_ids(user: User, db: AsyncSession) -> list[str] | None:
    """Compute the org IDs visible to the current user."""
    if user.is_superuser:
        return None  # sees everything
    org_svc = OrganizationService(db)
    return await org_svc.get_visible_org_ids(user.organization_id)


async def _assert_ticket_visible(ticket: Ticket, user: User, db: AsyncSession) -> None:
    """Raise NotFoundException if `ticket` is not in the caller's visible org scope (S-1)."""
    if user.is_superuser:
        return
    org_ids = await _get_visible_org_ids(user, db)
    if org_ids is not None and ticket.organization_id not in org_ids:
        raise NotFoundException("Ticket")


@router.get("/board", response_model=KanbanBoard)
async def get_kanban_board(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KanbanBoard:
    """Return all tickets grouped into Kanban columns by status."""
    org_ids = await _get_visible_org_ids(current_user, db)
    service = TicketService(db)
    all_tickets = await service.list_all(org_ids)

    board: dict[str, list[Ticket]] = {status.value: [] for status in TicketStatus}
    for ticket in all_tickets:
        board[ticket.status.value].append(ticket)

    return KanbanBoard(
        new=board["new"],
        working=board["working"],
        waiting=board["waiting"],
        resolved=board["resolved"],
        closed=board["closed"],
    )


@router.get("/", response_model=list[TicketSummary])
async def list_tickets(
    status: TicketStatus | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Ticket]:
    """List tickets visible to the current user, optionally filtered by status."""
    org_ids = await _get_visible_org_ids(current_user, db)
    service = TicketService(db)
    if status:
        return await service.list_by_status(status, org_ids)
    return await service.list_all(org_ids)


@router.post("/", response_model=TicketResponse, status_code=201)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    """Create a new ticket belonging to the current user's organisation."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=400,
            detail="User must belong to an organisation to create tickets",
        )
    service = TicketService(db)
    return await service.create(data, current_user.id, current_user.organization_id)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    """Fetch a single ticket by UUID, raising 404 if not found."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    """Partially update a ticket's fields."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    return await service.update(ticket, data, current_user.id)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: str,
    data: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    """Transition a ticket to a new status. Closing requires the close_ticket permission."""
    if data.status == TicketStatus.WAITING and not (data.note and data.note.strip()):
        raise ValidationException('"Waiting for" note is required when status is waiting')

    if data.status == TicketStatus.CLOSED and not current_user.is_superuser:
        user_service = UserService(db)
        has_close_permission = await user_service.user_has_permission(
            current_user.id, "close_ticket"
        )
        if not has_close_permission:
            raise ForbiddenException("Only schirrmeister or admin can close tickets")

    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    return await service.update_status(ticket, data, current_user.id)


@router.patch("/{ticket_id}/waiting-for", response_model=TicketResponse)
async def update_waiting_for(
    ticket_id: str,
    data: WaitingForUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    """Edit the 'waiting for' reason while the ticket is in waiting status."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    if ticket.status != TicketStatus.WAITING:
        raise ValidationException("Ticket is not in waiting status")
    return await service.update_waiting_for(ticket, data)


@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a ticket. Only the creator or a superuser may delete a ticket."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    if ticket.creator_id != current_user.id and not current_user.is_superuser:
        raise ForbiddenException()
    await service.delete(ticket)


# ─── Attachments ──────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    ticket_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """Upload a file attachment (image or PDF) to a ticket."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    attachment = await service.add_attachment(ticket, file, current_user.id)
    return AttachmentResponse.model_validate(attachment)


@router.delete("/{ticket_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    ticket_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an attachment from a ticket. Only the uploader or a superuser may delete it."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    await service.delete_attachment(attachment_id, current_user.id, current_user.is_superuser)


@router.get("/{ticket_id}/attachments/{attachment_id}/download")
async def download_attachment(
    ticket_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Download an attachment. Requires authentication; verifies the attachment
    belongs to the requested ticket and that the ticket is visible to the caller (A-5, S-1)."""
    # S-1: verify the ticket exists and is within the caller's org scope
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)

    result = await db.execute(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.ticket_id == ticket_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if attachment is None:
        raise NotFoundException("Attachment")

    # Path-traversal guard: resolve the stored path and confirm it sits inside
    # the configured upload root before serving the file (H-1).
    upload_root = Path(settings.UPLOAD_DIR).resolve()
    target = Path(attachment.file_path).resolve()
    if not str(target).startswith(str(upload_root)):
        raise NotFoundException("Attachment")

    return FileResponse(
        path=str(target),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


# ─── Comments ─────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    ticket_id: str,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Add a comment to a ticket."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    comment = await service.add_comment(ticket, data, current_user.id)
    return CommentResponse.model_validate(comment)


@router.patch("/{ticket_id}/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    ticket_id: str,
    comment_id: str,
    data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    """Edit a comment's content. Only the author or a superuser may edit it."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    comment = await service.update_comment(comment_id, ticket_id, data, current_user.id, current_user.is_superuser)
    return CommentResponse.model_validate(comment)


@router.delete("/{ticket_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    ticket_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a comment from a ticket. Only the author or a superuser may delete it."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    await service.delete_comment(comment_id, ticket_id, current_user.id, current_user.is_superuser)


# ─── Status Log ───────────────────────────────────────────────────────────────

@router.get("/{ticket_id}/status-log", response_model=list[StatusLogResponse])
async def get_status_log(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StatusLogResponse]:
    """Return the full status-change history for a ticket."""
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    await _assert_ticket_visible(ticket, current_user, db)
    return [StatusLogResponse.model_validate(log) for log in ticket.status_logs]
