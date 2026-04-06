"""initial schema – complete setup including seed data

Squashes the previous 0001-0005 migrations into a single clean migration.

Revision ID: 0001
Revises:
Create Date: 2026-04-04

"""
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import sqlalchemy as sa
import yaml
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── Seed data loader ──────────────────────────────────────────────────────────

_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def _load_seed(name: str) -> dict:  # type: ignore[type-arg]
    """Load a YAML seed file from backend/data/seed/."""
    with open(_SEED_DIR / name) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


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

    # ── seed: default priorities / categories ─────────────────────────────────
    seed_cfg = _load_seed("config_items.yaml")

    config_items_table = sa.table(
        "config_items",
        sa.column("id", sa.String),
        sa.column("type", sa.Enum("priority", "category", "group", name="configitemtype")),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    rows: list[dict] = []  # type: ignore[type-arg]
    for item in seed_cfg.get("priorities", []):
        rows.append({
            "id": str(uuid.uuid4()),
            "type": "priority",
            "name": item["name"],
            "sort_order": item.get("sort_order", 0),
            "is_active": True,
            "created_at": now,
        })
    for item in seed_cfg.get("categories", []):
        rows.append({
            "id": str(uuid.uuid4()),
            "type": "category",
            "name": item["name"],
            "sort_order": item.get("sort_order", 0),
            "is_active": True,
            "created_at": now,
        })
    if rows:
        op.bulk_insert(config_items_table, rows)

    # ── seed: core user groups ─────────────────────────────────────────────────
    seed_groups = _load_seed("user_groups.yaml")

    group_ids: dict[str, str] = {}
    user_groups_table = sa.table(
        "user_groups",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    group_rows = []
    for group_name in seed_groups.get("groups", []):
        gid = str(uuid.uuid4())
        group_ids[group_name] = gid
        group_rows.append({"id": gid, "name": group_name, "created_at": now})
    op.bulk_insert(user_groups_table, group_rows)

    # ── seed: initial admin user (users without organization, created pre-0002) ─
    seed_users = _load_seed("admin_users.yaml")
    initial_users = [u for u in seed_users.get("users", []) if not u.get("organization")]

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
    memberships_table = sa.table(
        "user_group_memberships",
        sa.column("user_id", sa.String),
        sa.column("group_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    for user_def in initial_users:
        uid = str(uuid.uuid4())
        hashed = bcrypt.hashpw(user_def["password"].encode(), bcrypt.gensalt()).decode()
        op.bulk_insert(users_table, [{
            "id": uid,
            "email": user_def["email"],
            "hashed_password": hashed,
            "full_name": user_def["full_name"],
            "is_active": True,
            "is_superuser": user_def.get("is_superuser", False),
            "force_password_change": user_def.get("force_password_change", True),
            "totp_secret": None,
            "totp_enabled": False,
            "created_at": now,
            "updated_at": now,
        }])
        membership_rows = []
        for grp in user_def.get("groups", []):
            gid = group_ids.get(grp)
            if gid:
                membership_rows.append({"user_id": uid, "group_id": gid, "created_at": now})
        if membership_rows:
            op.bulk_insert(memberships_table, membership_rows)

    # ── seed: age threshold settings ──────────────────────────────────────────
    seed_settings = _load_seed("app_settings.yaml")

    app_settings_table = sa.table(
        "app_settings",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        app_settings_table,
        [
            {"key": k, "value": v, "updated_at": now}
            for k, v in seed_settings.get("settings", {}).items()
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
