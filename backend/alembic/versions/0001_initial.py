"""initial schema – complete setup including seed data

Squashes the previous 0001-0005 migrations into a single clean migration.

Revision ID: 0001
Revises:
Create Date: 2026-04-04

"""
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import bcrypt
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("force_password_change", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ── config_items ──────────────────────────────────────────────────────────
    op.create_table(
        "config_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "type",
            sa.Enum("priority", "category", "group", name="configitemtype"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_config_items_type", "config_items", ["type"])

    # ── tickets ───────────────────────────────────────────────────────────────
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Enum("new", "working", "waiting", "resolved", "closed", name="ticketstatus"),
            nullable=False,
        ),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("priority_id", sa.String(36), sa.ForeignKey("config_items.id"), nullable=True),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("config_items.id"), nullable=True),
        sa.Column(
            "affected_group_id", sa.String(36), sa.ForeignKey("config_items.id"), nullable=True
        ),
        sa.Column("waiting_for", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_creator_id", "tickets", ["creator_id"])
    op.create_index("ix_tickets_owner_id", "tickets", ["owner_id"])

    # ── attachments ───────────────────────────────────────────────────────────
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("file_size", sa.Integer, nullable=False),
        sa.Column("uploaded_by_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_attachments_ticket_id", "attachments", ["ticket_id"])

    # ── comments ──────────────────────────────────────────────────────────────
    op.create_table(
        "comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_comments_ticket_id", "comments", ["ticket_id"])
    op.create_index("ix_comments_author_id", "comments", ["author_id"])

    # ── status_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "status_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id"), nullable=False),
        sa.Column("changed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "from_status",
            sa.Enum("new", "working", "waiting", "resolved", "closed", name="ticketstatus"),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum("new", "working", "waiting", "resolved", "closed", name="ticketstatus"),
            nullable=False,
        ),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_status_logs_ticket_id", "status_logs", ["ticket_id"])

    # ── user_groups ───────────────────────────────────────────────────────────
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_groups_name", "user_groups", ["name"], unique=True)

    # ── user_group_memberships ────────────────────────────────────────────────
    op.create_table(
        "user_group_memberships",
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column(
            "group_id", sa.String(36), sa.ForeignKey("user_groups.id"), primary_key=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── app_settings ──────────────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── seed: default priorities ──────────────────────────────────────────────
    config_items_table = sa.table(
        "config_items",
        sa.column("id", sa.String),
        sa.column("type", sa.Enum("priority", "category", "group", name="configitemtype")),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        config_items_table,
        [
            {
                "id": str(uuid.uuid4()),
                "type": "priority",
                "name": "Kritisch",
                "sort_order": 0,
                "is_active": True,
                "created_at": now,
            },
            {
                "id": str(uuid.uuid4()),
                "type": "priority",
                "name": "Hoch",
                "sort_order": 1,
                "is_active": True,
                "created_at": now,
            },
            {
                "id": str(uuid.uuid4()),
                "type": "priority",
                "name": "Mittel",
                "sort_order": 2,
                "is_active": True,
                "created_at": now,
            },
            {
                "id": str(uuid.uuid4()),
                "type": "priority",
                "name": "Gering",
                "sort_order": 3,
                "is_active": True,
                "created_at": now,
            },
        ],
    )

    # ── seed: core user groups ─────────────────────────────────────────────────
    helfende_id = str(uuid.uuid4())
    schirrmeister_id = str(uuid.uuid4())
    admin_group_id = str(uuid.uuid4())

    user_groups_table = sa.table(
        "user_groups",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        user_groups_table,
        [
            {"id": helfende_id, "name": "helfende", "created_at": now},
            {"id": schirrmeister_id, "name": "schirrmeister", "created_at": now},
            {"id": admin_group_id, "name": "admin", "created_at": now},
        ],
    )

    # ── seed: initial admin user ──────────────────────────────────────────────
    admin_user_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()

    users_table = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("full_name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_superuser", sa.Boolean),
        sa.column("force_password_change", sa.Boolean),
        sa.column("totp_secret", sa.String),
        sa.column("totp_enabled", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "id": admin_user_id,
                "email": "admin@example.com",
                "hashed_password": hashed,
                "full_name": "Admin",
                "is_active": True,
                "is_superuser": True,
                "force_password_change": True,
                "totp_secret": None,
                "totp_enabled": False,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    memberships_table = sa.table(
        "user_group_memberships",
        sa.column("user_id", sa.String),
        sa.column("group_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        memberships_table,
        [
            {"user_id": admin_user_id, "group_id": helfende_id, "created_at": now},
            {"user_id": admin_user_id, "group_id": admin_group_id, "created_at": now},
        ],
    )

    # ── seed: age threshold settings ──────────────────────────────────────────
    app_settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        app_settings_table,
        [
            {"key": "age_green_days", "value": "3", "updated_at": now},
            {"key": "age_light_green_days", "value": "7", "updated_at": now},
            {"key": "age_yellow_days", "value": "14", "updated_at": now},
            {"key": "age_orange_days", "value": "21", "updated_at": now},
            {"key": "age_light_red_days", "value": "30", "updated_at": now},
        ],
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("user_group_memberships")
    op.drop_index("ix_user_groups_name", table_name="user_groups")
    op.drop_table("user_groups")
    op.drop_index("ix_status_logs_ticket_id", table_name="status_logs")
    op.drop_table("status_logs")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_ticket_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_attachments_ticket_id", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_tickets_owner_id", table_name="tickets")
    op.drop_index("ix_tickets_creator_id", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_config_items_type", table_name="config_items")
    op.drop_table("config_items")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
