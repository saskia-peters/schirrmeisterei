import io
import os
from pathlib import Path

import aiofiles
import aiofiles.os
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.models import Attachment, Comment, StatusLog, Ticket, TicketStatus, User
from app.schemas.ticket import CommentCreate, CommentUpdate, TicketCreate, TicketStatusUpdate, TicketUpdate, WaitingForUpdate
from app.services.totp_service import get_safe_upload_path

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

_PILLOW_FORMAT_TO_MIME: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "GIF": "image/gif",
    "WEBP": "image/webp",
}


def _detect_image_mime(data: bytes) -> str | None:
    """Return the MIME type inferred from the file's magic bytes via Pillow.

    Returns None if the data is not a recognised image format, or if Pillow
    cannot parse the header at all.  This prevents content-type spoofing: the
    client-supplied Content-Type header is ignored entirely.
    """
    try:
        fmt = Image.open(io.BytesIO(data)).format
        return _PILLOW_FORMAT_TO_MIME.get(fmt or "")
    except (UnidentifiedImageError, Exception):  # noqa: BLE001
        return None


class TicketService:
    def __init__(self, db: AsyncSession) -> None:
        """Initialise the service with a database session."""
        self.db = db

    async def get_by_id(self, ticket_id: str) -> Ticket | None:
        """Fetch a Ticket by UUID with all relationships loaded, or None if not found."""
        result = await self.db.execute(
            select(Ticket)
            .execution_options(populate_existing=True)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.organization),
                selectinload(Ticket.creator).selectinload(User.organization),
                selectinload(Ticket.owner).selectinload(User.organization),
                selectinload(Ticket.priority),
                selectinload(Ticket.category),
                selectinload(Ticket.affected_group),
                selectinload(Ticket.attachments),
                selectinload(Ticket.comments).selectinload(Comment.author).selectinload(User.organization),
                selectinload(Ticket.status_logs),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, ticket_id: str) -> Ticket:
        """Fetch a Ticket by UUID, raising NotFoundException if it does not exist."""
        ticket = await self.get_by_id(ticket_id)
        if ticket is None:
            raise NotFoundException("Ticket")
        return ticket

    async def list_all(self, org_ids: list[str] | None = None) -> list[Ticket]:
        """Return all tickets, optionally restricted to the given organisation IDs."""
        # SCALE-UP (P-3): at higher ticket counts split this into two option sets:
        #   _ticket_summary_options()  -- id/title/status/priority/org/assignee only
        #   _ticket_detail_options()   -- full graph incl. comments + status_logs
        # Use summary options for list/board, detail options for GET /{id}.
        # See SCALING.md § Query Optimisation and REVIEW.md P-2/P-3.
        stmt = select(Ticket).options(
            selectinload(Ticket.organization),
            selectinload(Ticket.creator).selectinload(User.organization),
            selectinload(Ticket.owner).selectinload(User.organization),
            selectinload(Ticket.priority),
            selectinload(Ticket.category),
            selectinload(Ticket.affected_group),
            selectinload(Ticket.attachments),
            selectinload(Ticket.comments).selectinload(Comment.author).selectinload(User.organization),
            selectinload(Ticket.status_logs),
        )
        if org_ids is not None:
            stmt = stmt.where(Ticket.organization_id.in_(org_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: TicketStatus, org_ids: list[str] | None = None) -> list[Ticket]:
        """Return tickets with the given status, optionally restricted to the given org IDs."""
        stmt = (
            select(Ticket)
            .where(Ticket.status == status)
            .options(
                selectinload(Ticket.organization),
                selectinload(Ticket.creator).selectinload(User.organization),
                selectinload(Ticket.owner).selectinload(User.organization),
                selectinload(Ticket.priority),
                selectinload(Ticket.category),
                selectinload(Ticket.affected_group),
                selectinload(Ticket.attachments),
                selectinload(Ticket.comments).selectinload(Comment.author).selectinload(User.organization),
                selectinload(Ticket.status_logs),
            )
        )
        if org_ids is not None:
            stmt = stmt.where(Ticket.organization_id.in_(org_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: TicketCreate, creator_id: str, organization_id: str | None = None) -> Ticket:
        """Create a new ticket, log its initial status and return it with all relationships loaded."""
        ticket = Ticket(
            title=data.title,
            description=data.description,
            creator_id=creator_id,
            owner_id=data.assignee_id,
            organization_id=organization_id,
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
        """Apply TicketUpdate fields to the ticket, log assignee changes, and flush."""
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
        """Transition the ticket to the new status, handle waiting-for notes and log the change."""
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
        """Delete a ticket from the database."""
        await self.db.delete(ticket)
        await self.db.flush()

    # ─── Attachments ──────────────────────────────────────────────────────────

    async def add_attachment(
        self, ticket: Ticket, file: UploadFile, user_id: str
    ) -> Attachment:
        """Validate, save and persist a file attachment for the given ticket."""
        max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        # SCALE-UP (P-4): at higher user counts read the file in chunks to avoid
        # buffering the entire upload in memory before the size check:
        #   buf = b""
        #   async for chunk in file:
        #       buf += chunk
        #       if len(buf) > max_size:
        #           raise ValidationException(...)
        #   contents = buf
        # Also add `client_max_body_size 11M;` to nginx.conf at the same time.
        # See SCALING.md § File Uploads.
        contents = await file.read()
        if len(contents) > max_size:
            from app.core.exceptions import ValidationException
            raise ValidationException(
                f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        # Validate actual file content via magic bytes (Pillow reads the file
        # header) rather than the client-supplied Content-Type, which can be
        # trivially spoofed to upload HTML/script files as images (C-3).
        detected_mime = _detect_image_mime(contents)
        if not detected_mime:
            from app.core.exceptions import ValidationException
            raise ValidationException(
                f"File does not appear to be a valid image. "
                f"Allowed types: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
            )

        # Attachments live in a dedicated subdirectory, separate from avatars.
        # get_safe_upload_path further splits into 256 shard dirs (first 2 hex
        # chars of UUID) so no single directory accumulates thousands of files.
        attachment_dir = os.path.join(settings.UPLOAD_DIR, "attachments")
        os.makedirs(attachment_dir, exist_ok=True)

        safe_path = get_safe_upload_path(attachment_dir, file.filename or "upload")
        async with aiofiles.open(safe_path, "wb") as f:
            await f.write(contents)

        attachment = Attachment(
            ticket_id=ticket.id,
            filename=file.filename or "upload",
            content_type=detected_mime,  # use server-detected type, not client header
            file_path=safe_path,
            file_size=len(contents),
            uploaded_by_id=user_id,
        )
        self.db.add(attachment)
        await self.db.flush()
        await self.db.refresh(attachment)
        return attachment

    async def delete_attachment(self, attachment_id: str, user_id: str, is_superuser: bool) -> None:
        """Delete an attachment record and its corresponding file from disk."""
        result = await self.db.execute(select(Attachment).where(Attachment.id == attachment_id))
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise NotFoundException("Attachment")
        if attachment.uploaded_by_id != user_id and not is_superuser:
            raise ForbiddenException()

        upload_root = Path(settings.UPLOAD_DIR).resolve()
        target = Path(attachment.file_path).resolve()
        if not str(target).startswith(str(upload_root)):
            raise ForbiddenException()

        if await aiofiles.os.path.exists(attachment.file_path):
            await aiofiles.os.remove(attachment.file_path)

        await self.db.delete(attachment)
        await self.db.flush()

    # ─── Comments ─────────────────────────────────────────────────────────────

    async def add_comment(self, ticket: Ticket, data: CommentCreate, user_id: str) -> Comment:
        """Append a new comment to the ticket and return the persisted Comment."""
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
        self, comment_id: str, ticket_id: str, data: CommentUpdate, user_id: str, is_superuser: bool
    ) -> Comment:
        """Update a comment's content. Raises ForbiddenException if the caller is not the author.

        `ticket_id` is required and must match the comment's own ticket_id (S-2): this
        prevents a caller from editing a comment on a different ticket by supplying a
        mismatched (ticket_id, comment_id) pair.
        """
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id)
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            raise NotFoundException("Comment")
        if comment.author_id != user_id and not is_superuser:
            raise ForbiddenException()
        comment.content = data.content
        await self.db.flush()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, comment_id: str, ticket_id: str, user_id: str, is_superuser: bool) -> None:
        """Delete a comment. Raises ForbiddenException if the caller is not the author.

        `ticket_id` is required and must match the comment's own ticket_id (S-2): this
        prevents a caller from deleting a comment on a different ticket by supplying a
        mismatched (ticket_id, comment_id) pair.
        """
        result = await self.db.execute(
            select(Comment).where(Comment.id == comment_id, Comment.ticket_id == ticket_id)
        )
        comment = result.scalar_one_or_none()
        if comment is None:
            raise NotFoundException("Comment")
        if comment.author_id != user_id and not is_superuser:
            raise ForbiddenException()
        await self.db.delete(comment)
        await self.db.flush()
