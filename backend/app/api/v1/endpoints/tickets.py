from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.exceptions import ForbiddenException, NotFoundException, ValidationException
from app.db.session import get_db
from app.models.models import Ticket, TicketStatus, User
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
)
from app.services.ticket_service import TicketService
from app.services.user_service import UserService

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/board", response_model=KanbanBoard)
async def get_kanban_board(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> KanbanBoard:
    service = TicketService(db)
    all_tickets = await service.list_all()

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
    _: User = Depends(get_current_user),
) -> list[Ticket]:
    service = TicketService(db)
    if status:
        return await service.list_by_status(status)
    return await service.list_all()


@router.post("/", response_model=TicketResponse, status_code=201)
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    service = TicketService(db)
    return await service.create(data, current_user.id)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Ticket:
    service = TicketService(db)
    return await service.get_by_id_or_raise(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    return await service.update(ticket, data, current_user.id)


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: str,
    data: TicketStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Ticket:
    if data.status == TicketStatus.WAITING and not (data.note and data.note.strip()):
        raise ValidationException('"Waiting for" note is required when status is waiting')

    if data.status == TicketStatus.CLOSED and not current_user.is_superuser:
        user_service = UserService(db)
        has_close_permission = await user_service.user_has_any_group(
            current_user.id,
            {"schirrmeister", "admin"},
        )
        if not has_close_permission:
            raise ForbiddenException("Only schirrmeister or admin can close tickets")

    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    return await service.update_status(ticket, data, current_user.id)


@router.delete("/{ticket_id}", status_code=204)
async def delete_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
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
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    attachment = await service.add_attachment(ticket, file, current_user.id)
    return AttachmentResponse.model_validate(attachment)


@router.delete("/{ticket_id}/attachments/{attachment_id}", status_code=204)
async def delete_attachment(
    ticket_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = TicketService(db)
    await service.get_by_id_or_raise(ticket_id)
    await service.delete_attachment(attachment_id, current_user.id, current_user.is_superuser)


# ─── Comments ─────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    ticket_id: str,
    data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentResponse:
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
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
    service = TicketService(db)
    await service.get_by_id_or_raise(ticket_id)
    comment = await service.update_comment(comment_id, data, current_user.id, current_user.is_superuser)
    return CommentResponse.model_validate(comment)


@router.delete("/{ticket_id}/comments/{comment_id}", status_code=204)
async def delete_comment(
    ticket_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    service = TicketService(db)
    await service.get_by_id_or_raise(ticket_id)
    await service.delete_comment(comment_id, current_user.id, current_user.is_superuser)


# ─── Status Log ───────────────────────────────────────────────────────────────

@router.get("/{ticket_id}/status-log", response_model=list[StatusLogResponse])
async def get_status_log(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[StatusLogResponse]:
    service = TicketService(db)
    ticket = await service.get_by_id_or_raise(ticket_id)
    return [StatusLogResponse.model_validate(log) for log in ticket.status_logs]
