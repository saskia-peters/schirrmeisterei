import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TicketStatus(str, enum.Enum):
    NEW = "new"
    WORKING = "working"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ConfigItemType(str, enum.Enum):
    PRIORITY = "priority"
    CATEGORY = "category"
    GROUP = "group"


class UserGroupName(str, enum.Enum):
    HELFENDE = "helfende"
    SCHIRRMEISTER = "schirrmeister"
    ADMIN = "admin"


class ConfigItem(Base):
    __tablename__ = "config_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[ConfigItemType] = mapped_column(
        Enum(ConfigItemType, values_callable=lambda e: [x.value for x in e], create_constraint=False),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    priority_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="priority", foreign_keys="Ticket.priority_id"
    )
    category_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="category", foreign_keys="Ticket.category_id"
    )
    group_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="affected_group", foreign_keys="Ticket.affected_group_id"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    force_password_change: Mapped[bool] = mapped_column(Boolean, default=False)
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    created_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="creator", foreign_keys="Ticket.creator_id"
    )
    owned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket", back_populates="owner", foreign_keys="Ticket.owner_id"
    )
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="author")
    status_log_entries: Mapped[list["StatusLog"]] = relationship(
        "StatusLog", back_populates="changed_by_user"
    )
    group_memberships: Mapped[list["UserGroupMembership"]] = relationship(
        "UserGroupMembership", back_populates="user", cascade="all, delete-orphan"
    )
    groups: Mapped[list["UserGroup"]] = relationship(
        "UserGroup",
        secondary="user_group_memberships",
        back_populates="users",
        viewonly=True,
    )


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    memberships: Mapped[list["UserGroupMembership"]] = relationship(
        "UserGroupMembership", back_populates="group", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary="user_group_memberships",
        back_populates="groups",
        viewonly=True,
    )


class UserGroupMembership(Base):
    __tablename__ = "user_group_memberships"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_groups.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="group_memberships")
    group: Mapped["UserGroup"] = relationship("UserGroup", back_populates="memberships")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, values_callable=lambda e: [x.value for x in e], create_constraint=False),
        default=TicketStatus.NEW,
        nullable=False,
        index=True
    )
    creator_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    owner_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    priority_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("config_items.id"), nullable=True, index=True
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("config_items.id"), nullable=True, index=True
    )
    affected_group_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("config_items.id"), nullable=True, index=True
    )
    waiting_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    creator: Mapped["User"] = relationship(
        "User", back_populates="created_tickets", foreign_keys=[creator_id]
    )
    owner: Mapped["User | None"] = relationship(
        "User", back_populates="owned_tickets", foreign_keys=[owner_id]
    )
    priority: Mapped["ConfigItem | None"] = relationship(
        "ConfigItem", back_populates="priority_tickets", foreign_keys=[priority_id]
    )
    category: Mapped["ConfigItem | None"] = relationship(
        "ConfigItem", back_populates="category_tickets", foreign_keys=[category_id]
    )
    affected_group: Mapped["ConfigItem | None"] = relationship(
        "ConfigItem", back_populates="group_tickets", foreign_keys=[affected_group_id]
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="ticket", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="ticket", cascade="all, delete-orphan"
    )
    status_logs: Mapped[list["StatusLog"]] = relationship(
        "StatusLog", back_populates="ticket", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    uploaded_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="attachments")
    uploaded_by: Mapped["User"] = relationship("User")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=False, index=True
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
    author: Mapped["User"] = relationship("User", back_populates="comments")


class StatusLog(Base):
    __tablename__ = "status_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tickets.id"), nullable=False, index=True
    )
    changed_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    from_status: Mapped[TicketStatus | None] = mapped_column(
        Enum(TicketStatus, values_callable=lambda e: [x.value for x in e], create_constraint=False),
        nullable=True,
    )
    to_status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, values_callable=lambda e: [x.value for x in e], create_constraint=False),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="status_logs")
    changed_by_user: Mapped["User"] = relationship("User", back_populates="status_log_entries")


class AppSetting(Base):
    """Key-value store for application-wide configuration (e.g. age thresholds)."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
