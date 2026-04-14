from datetime import datetime

from pydantic import BaseModel, Field, computed_field, model_validator
from typing import Any

from app.models.models import ORG_LEVEL_ABBREV


def _user_display_name(user: Any) -> str:
    """Return 'Full Name (OV)' if the user has an organization, else just the name."""
    if user is None:
        return ""
    name = user.full_name
    if hasattr(user, "organization") and user.organization is not None:
        abbrev = ORG_LEVEL_ABBREV.get(user.organization.level, "")
        if abbrev:
            name = f"{name} ({abbrev})"
    return name

from app.models.models import TicketStatus


# ─── Attachment ───────────────────────────────────────────────────────────────

class AttachmentResponse(BaseModel):
    id: str
    ticket_id: str
    filename: str
    content_type: str
    file_size: int
    uploaded_by_id: str
    created_at: datetime
    # file_path is intentionally omitted — it exposes the internal server path
    # (H-4). Clients should use the `url` field instead.

    @computed_field  # type: ignore[misc]
    @property
    def url(self) -> str:
        """Authenticated download URL for this attachment (A-5)."""
        return f"/tickets/{self.ticket_id}/attachments/{self.id}/download"

    model_config = {"from_attributes": True}


# ─── Comment ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    id: str
    ticket_id: str
    author_id: str
    author_name: str = ""
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_author_name(cls, data: Any) -> Any:
        if hasattr(data, "author") and data.author is not None:
            return {
                "id": data.id,
                "ticket_id": data.ticket_id,
                "author_id": data.author_id,
                "author_name": _user_display_name(data.author),
                "content": data.content,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


# ─── Status Log ───────────────────────────────────────────────────────────────

class StatusLogResponse(BaseModel):
    id: str
    ticket_id: str
    changed_by: str
    from_status: TicketStatus | None
    to_status: TicketStatus
    note: str | None
    changed_at: datetime

    model_config = {"from_attributes": True}


# ─── Ticket ───────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=50000)
    assignee_id: str | None = None
    priority_id: str | None = None
    category_id: str | None = None
    affected_group_id: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1, max_length=50000)
    assignee_id: str | None = None
    priority_id: str | None = None
    category_id: str | None = None
    affected_group_id: str | None = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    note: str | None = Field(None, max_length=1000)


class WaitingForUpdate(BaseModel):
    waiting_for: str | None = Field(None, max_length=1000)


class TicketResponse(BaseModel):
    id: str
    ticket_number: int
    title: str
    description: str
    status: TicketStatus
    creator_id: str
    assignee_id: str | None
    assignee_name: str | None
    assignee_avatar_url: str | None = None
    organization_id: str | None = None
    priority_id: str | None
    priority_name: str | None
    category_id: str | None
    category_name: str | None
    affected_group_id: str | None
    affected_group_name: str | None
    waiting_for: str | None
    watcher_ids: list[str] = []
    created_at: datetime
    updated_at: datetime
    attachments: list[AttachmentResponse] = []
    comments: list[CommentResponse] = []
    status_logs: list[StatusLogResponse] = []

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_assignee(cls, data: Any) -> Any:
        if not hasattr(data, "owner_id"):
            return data
        return {
            "id": data.id,
            "ticket_number": data.ticket_number,
            "title": data.title,
            "description": data.description,
            "status": data.status,
            "creator_id": data.creator_id,
            "assignee_id": data.owner_id,
            "assignee_name": _user_display_name(data.owner) or None,
            "assignee_avatar_url": data.owner.avatar_url if data.owner else None,
            "organization_id": data.organization_id,
            "priority_id": data.priority_id,
            "priority_name": data.priority.name if data.priority is not None else None,
            "category_id": data.category_id,
            "category_name": data.category.name if data.category is not None else None,
            "affected_group_id": data.affected_group_id,
            "affected_group_name": data.affected_group.name if data.affected_group is not None else None,
            "waiting_for": data.waiting_for,
            "watcher_ids": [w.user_id for w in data.watchers] if hasattr(data, "watchers") else [],
            "created_at": data.created_at,
            "updated_at": data.updated_at,
            "attachments": list(data.attachments),
            "comments": list(data.comments),
            "status_logs": list(data.status_logs),
        }


class TicketSummary(BaseModel):
    id: str
    ticket_number: int
    title: str
    status: TicketStatus
    creator_id: str
    creator_name: str = ""
    assignee_id: str | None = None
    assignee_name: str | None = None
    assignee_avatar_url: str | None = None
    organization_id: str | None = None
    organization_name: str | None = None
    priority_id: str | None = None
    priority_name: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    affected_group_id: str | None = None
    affected_group_name: str | None = None
    waiting_for: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_names(cls, data: Any) -> Any:
        if not hasattr(data, "creator_id"):
            return data
        org = getattr(data, "organization", None)
        return {
            "id": data.id,
            "ticket_number": data.ticket_number,
            "title": data.title,
            "status": data.status,
            "creator_id": data.creator_id,
            "creator_name": _user_display_name(data.creator),
            "assignee_id": data.owner_id,
            "assignee_name": _user_display_name(data.owner) or None,
            "assignee_avatar_url": data.owner.avatar_url if data.owner else None,
            "organization_id": data.organization_id,
            "organization_name": org.name if org else None,
            "priority_id": data.priority_id,
            "priority_name": data.priority.name if data.priority is not None else None,
            "category_id": data.category_id,
            "category_name": data.category.name if data.category is not None else None,
            "affected_group_id": data.affected_group_id,
            "affected_group_name": data.affected_group.name if data.affected_group is not None else None,
            "waiting_for": data.waiting_for,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class KanbanBoard(BaseModel):
    new: list[TicketSummary]
    working: list[TicketSummary]
    waiting: list[TicketSummary]
    resolved: list[TicketSummary]
    closed: list[TicketSummary]
