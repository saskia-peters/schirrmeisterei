import os

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.models import Attachment, Comment, StatusLog, Ticket, TicketStatus, User
from app.schemas.ticket import CommentCreate, CommentUpdate, TicketCreate, TicketStatusUpdate, TicketUpdate, WaitingForUpdate
from app.services.totp_service import get_safe_upload_path

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class TicketService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, ticket_id: str) -> Ticket | None:
        result = await self.db.execute(
            select(Ticket)
            .execution_options(populate_existing=True)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.creator),
                selectinload(Ticket.owner),
                selectinload(Ticket.priority),
                selectinload(Ticket.category),
                selectinload(Ticket.affected_group),
                selectinload(Ticket.attachments),
                selectinload(Ticket.comments).selectinload(Comment.author),
                selectinload(Ticket.status_logs),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, ticket_id: str) -> Ticket:
        ticket = await self.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException("Ticket")
        return ticket

    async def list_all(self) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket).options(
                selectinload(Ticket.creator),
                selectinload(Ticket.owner),
                selectinload(Ticket.priority),
                selectinload(Ticket.category),
                selectinload(Ticket.affected_group),
                selectinload(Ticket.attachments),
                selectinload(Ticket.comments).selectinload(Comment.author),
                selectinload(Ticket.status_logs),
            )
        )
        return list(result.scalars().all())

    async def list_by_status(self, status: TicketStatus) -> list[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.status == status)
            .options(
                selectinload(Ticket.creator),
                selectinload(Ticket.owner),
                selectinload(Ticket.priority),
                selectinload(Ticket.category),
                selectinload(Ticket.affected_group),
                selectinload(Ticket.attachments),
                selectinload(Ticket.comments).selectinload(Comment.author),
                selectinload(Ticket.status_logs),
            )
        )
        return list(result.scalars().all())

    async def create(self, data: TicketCreate, creator_id: str) -> Ticket:
        ticket = Ticket(
            title=data.title,
            description=data.description,
            creator_id=creator_id,
            owner_id=data.assignee_id,
            priority_id=data.priority_id,
            category_id=data.category_id,
            affected_group_id=data.affected_group_id,
            status=TicketStatus.NEW,
        )
        self.db.add(ticket)
        await self.db.flush()

        # Log initial status
        log = StatusLog(
            ticket_id=ticket.id,
            changed_by=creator_id,
            from_status=None,
            to_status=TicketStatus.NEW,
            note="Ticket created",
        )
        self.db.add(log)
        await self.db.flush()

        # Reload with relationships so async serialization works
        return await self.get_by_id_or_raise(ticket.id)

    async def update(self, ticket: Ticket, data: TicketUpdate, user_id: str) -> Ticket:
        if data.title is not None:
            ticket.title = data.title
        if data.description is not None:
            ticket.description = data.description
        if "priority_id" in data.model_fields_set:
            ticket.priority_id = data.priority_id
        if "category_id" in data.model_fields_set:
            ticket.category_id = data.category_id
        if "affected_group_id" in data.model_fields_set:
            ticket.affected_group_id = data.affected_group_id

        if "assignee_id" in data.model_fields_set:
            old_name = ticket.owner.full_name if ticket.owner is not None else None
            old_owner_id = ticket.owner_id
            ticket.owner_id = data.assignee_id
            await self.db.flush()

            if old_owner_id != data.assignee_id:
                # Resolve new owner name
                new_name: str | None = None
                if data.assignee_id is not None:
                    result = await self.db.execute(
                        select(User).where(User.id == data.assignee_id)
                    )
                    new_user = result.scalar_one_or_none()
                    if new_user:
                        new_name = new_user.full_name

                log = StatusLog(
                    ticket_id=ticket.id,
                    changed_by=user_id,
                    from_status=ticket.status,
                    to_status=ticket.status,
                    note=f"Assignee changed: {old_name or 'Unassigned'} → {new_name or 'Unassigned'}",
                )
                self.db.add(log)

        await self.db.flush()
        return await self.get_by_id_or_raise(ticket.id)

    async def update_status(
        self, ticket: Ticket, data: TicketStatusUpdate, user_id: str
    ) -> Ticket:
        old_status = ticket.status
        old_waiting_for = ticket.waiting_for
        ticket.status = data.status

        # When moving TO waiting, store reason directly on ticket
        if data.status == TicketStatus.WAITING and data.note:
            ticket.waiting_for = data.note.strip() or None

        # When moving AWAY from waiting, auto-comment with the reason and clear the field
        if old_status == TicketStatus.WAITING and data.status != TicketStatus.WAITING:
            if old_waiting_for:
                auto_comment = Comment(
                    ticket_id=ticket.id,
                    author_id=user_id,
                    content=f"Has been waiting for: {old_waiting_for}",
                )
                self.db.add(auto_comment)
            ticket.waiting_for = None

        log = StatusLog(
            ticket_id=ticket.id,
            changed_by=user_id,
            from_status=old_status,
            to_status=data.status,
            note=data.note,
        )
        self.db.add(log)
        await self.db.flush()
        return await self.get_by_id_or_raise(ticket.id)

    async def update_waiting_for(
        self, ticket: Ticket, data: WaitingForUpdate
    ) -> Ticket:
        """Edit the waiting-for reason while a ticket remains in waiting status."""
        ticket.waiting_for = data.waiting_for.strip() if data.waiting_for else None
        await self.db.flush()
        return await self.get_by_id_or_raise(ticket.id)

    async def delete(self, ticket: Ticket) -> None:
        await self.db.delete(ticket)
        await self.db.flush()

    # ─── Attachments ──────────────────────────────────────────────────────────

    async def add_attachment(
        self, ticket: Ticket, file: UploadFile, user_id: str
    ) -> Attachment:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            from app.core.exceptions import ValidationException
            raise ValidationException(
                f"File type {file.content_type} not allowed. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )

        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_size:
            from app.core.exceptions import ValidationException
            raise ValidationException(
                f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        upload_dir = settings.UPLOAD_DIR
        os.makedirs(upload_dir, exist_ok=True)

        safe_path = get_safe_upload_path(upload_dir, file.filename or "upload")
        async with aiofiles.open(safe_path, "wb") as f:
            await f.write(contents)

        attachment = Attachment(
            ticket_id=ticket.id,
            filename=file.filename or "upload",
            content_type=file.content_type,
            file_path=safe_path,
            file_size=len(contents),
            uploaded_by_id=user_id,
        )
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    async def delete_attachment(self, attachment_id: str, user_id: str, is_superuser: bool) -> None:
        result = await self.db.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise NotFoundException("Attachment")
        if attachment.uploaded_by_id != user_id and not is_superuser:
            raise ForbiddenException()

        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)

        await self.db.delete(attachment)
        await self.db.flush()

    # ─── Comments ─────────────────────────────────────────────────────────────

    async def add_comment(self, ticket: Ticket, data: CommentCreate, user_id: str) -> Comment:
        comment = Comment(
            ticket_id=ticket.id,
            author_id=user_id,
            content=data.content,
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def update_comment(
        self, comment_id: str, data: CommentUpdate, user_id: str, is_superuser: bool
    ) -> Comment:
        result = await self.db.execute(select(Comment).where(Comment.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment is None:
            raise NotFoundException("Comment")
        if comment.author_id != user_id and not is_superuser:
            raise ForbiddenException()
        comment.content = data.content
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, comment_id: str, user_id: str, is_superuser: bool) -> None:
        result = await self.db.execute(select(Comment).where(Comment.id == comment_id))
        comment = result.scalar_one_or_none()
        if comment is None:
            raise NotFoundException("Comment")
        if comment.author_id != user_id and not is_superuser:
            raise ForbiddenException()
        await self.db.delete(comment)
        await self.db.flush()
