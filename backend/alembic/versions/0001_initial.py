"""initial schema – complete setup including seed data

Revision ID: 0001
Revises:
Create Date: 2026-04-11

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
    conn = op.get_bind()

    # ══════════════════════════════════════════════════════════════════════════
    # SCHEMA
    # ══════════════════════════════════════════════════════════════════════════

    # ── organizations ─────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "level",
            sa.Enum("ortsverband", "regionalstelle", "landesverband", "leitung",
                    name="organizationlevel"),
            nullable=False,
        ),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organizations_level", "organizations", ["level"])
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"])

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("force_password_change", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("totp_secret", sa.String(64), nullable=True),
        sa.Column("totp_enabled", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

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
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id"), nullable=True,
        ),
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
    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"])

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

    # ── user_groups (with org-scoped roles) ───────────────────────────────────
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_user_groups_name_org",
        "user_groups",
        [sa.text("name"), sa.text("COALESCE(organization_id, '')")],
        unique=True,
    )
    op.create_index(
        "ix_user_groups_organization_id", "user_groups", ["organization_id"],
    )

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

    # ── permissions ───────────────────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("codename", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_permissions_codename", "permissions", ["codename"], unique=True)

    # ── role_permissions ──────────────────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("user_groups.id"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── email_configs ─────────────────────────────────────────────────────────
    op.create_table(
        "email_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id", sa.String(36),
            sa.ForeignKey("organizations.id"), nullable=False, unique=True,
        ),
        sa.Column("smtp_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer, nullable=False, server_default="587"),
        sa.Column("smtp_user", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_password", sa.String(255), nullable=False, server_default=""),
        sa.Column("from_email", sa.String(255), nullable=False, server_default=""),
        sa.Column("use_tls", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── app_settings ──────────────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ══════════════════════════════════════════════════════════════════════════
    # SEED DATA
    # ══════════════════════════════════════════════════════════════════════════

    # ── seed: organizations ───────────────────────────────────────────────────
    seed_orgs = _load_seed("organisations.yaml")
    org_ids: dict[str, str] = {}  # name -> id

    for entry in seed_orgs.get("hierarchy", []):
        oid = str(uuid.uuid4())
        org_ids[entry["name"]] = oid
        conn.execute(
            sa.text(
                "INSERT INTO organizations (id, name, level, parent_id, created_at) "
                "VALUES (:id, :name, CAST(:level AS organizationlevel), :parent_id, :created_at)"
            ),
            {
                "id": oid,
                "name": entry["name"],
                "level": entry["level"],
                "parent_id": org_ids.get(entry.get("parent", "")) or None,
                "created_at": now,
            },
        )

    # ── seed: config items (priorities / categories) ──────────────────────────
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
    cfg_rows: list[dict] = []  # type: ignore[type-arg]
    for item in seed_cfg.get("priorities", []):
        cfg_rows.append({
            "id": str(uuid.uuid4()),
            "type": "priority",
            "name": item["name"],
            "sort_order": item.get("sort_order", 0),
            "is_active": True,
            "created_at": now,
        })
    for item in seed_cfg.get("categories", []):
        cfg_rows.append({
            "id": str(uuid.uuid4()),
            "type": "category",
            "name": item["name"],
            "sort_order": item.get("sort_order", 0),
            "is_active": True,
            "created_at": now,
        })
    if cfg_rows:
        op.bulk_insert(config_items_table, cfg_rows)

    # ── seed: template role groups (org_id = NULL) ────────────────────────────
    seed_groups = _load_seed("user_groups.yaml")
    template_ids: dict[str, str] = {}  # group name -> template group id

    user_groups_table = sa.table(
        "user_groups",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("organization_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    for group_name in seed_groups.get("groups", []):
        gid = str(uuid.uuid4())
        template_ids[group_name] = gid
        op.bulk_insert(user_groups_table, [{
            "id": gid,
            "name": group_name,
            "organization_id": None,
            "created_at": now,
        }])

    # ── seed: permissions ─────────────────────────────────────────────────────
    seed_perms = _load_seed("permissions.yaml")
    perm_ids: dict[str, str] = {}  # codename -> permission id

    perms_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("codename", sa.String),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    for perm in seed_perms.get("permissions", []):
        pid = str(uuid.uuid4())
        perm_ids[perm["codename"]] = pid
        op.bulk_insert(perms_table, [{
            "id": pid,
            "codename": perm["codename"],
            "description": perm["description"],
            "created_at": now,
        }])

    # ── seed: role_permissions (template roles) ───────────────────────────────
    seed_rp = _load_seed("role_permissions.yaml")

    rp_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    # Build template permissions map for cloning later
    template_perms: dict[str, list[str]] = {}  # template_group_id -> [perm_id, ...]
    for role_name, perm_codenames in seed_rp.get("role_permissions", {}).items():
        rid = template_ids.get(role_name)
        if not rid:
            continue
        template_perms[rid] = []
        for codename in perm_codenames:
            pid = perm_ids.get(codename)
            if not pid:
                continue
            template_perms[rid].append(pid)
            op.bulk_insert(rp_table, [{"role_id": rid, "permission_id": pid, "created_at": now}])

    # ── seed: clone template roles into each organization ─────────────────────
    # mapping: (template_group_id, org_id) -> new_group_id
    cloned_map: dict[tuple[str, str], str] = {}

    for org_name, org_id in org_ids.items():
        for tname, tid in template_ids.items():
            new_gid = str(uuid.uuid4())
            cloned_map[(tid, org_id)] = new_gid

            op.bulk_insert(user_groups_table, [{
                "id": new_gid,
                "name": tname,
                "organization_id": org_id,
                "created_at": now,
            }])

            # Clone role_permissions
            for perm_id in template_perms.get(tid, []):
                op.bulk_insert(rp_table, [{
                    "role_id": new_gid,
                    "permission_id": perm_id,
                    "created_at": now,
                }])

    # ── seed: admin users ─────────────────────────────────────────────────────
    seed_users = _load_seed("admin_users.yaml")

    users_table = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("email", sa.String),
        sa.column("hashed_password", sa.String),
        sa.column("full_name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("is_superuser", sa.Boolean),
        sa.column("is_approved", sa.Boolean),
        sa.column("force_password_change", sa.Boolean),
        sa.column("totp_secret", sa.String),
        sa.column("totp_enabled", sa.Boolean),
        sa.column("avatar_url", sa.String),
        sa.column("organization_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    memberships_table = sa.table(
        "user_group_memberships",
        sa.column("user_id", sa.String),
        sa.column("group_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    for user_def in seed_users.get("users", []):
        uid = str(uuid.uuid4())
        hashed = bcrypt.hashpw(user_def["password"].encode(), bcrypt.gensalt()).decode()

        # Resolve organization
        user_org_name = user_def.get("organization")
        if user_org_name:
            user_org_id = org_ids.get(user_org_name)
        elif user_def.get("is_superuser"):
            # Superusers without explicit org → assign to THW-Leitung
            user_org_id = org_ids.get("THW-Leitung")
        else:
            user_org_id = None

        op.bulk_insert(users_table, [{
            "id": uid,
            "email": user_def["email"],
            "hashed_password": hashed,
            "full_name": user_def["full_name"],
            "is_active": True,
            "is_superuser": user_def.get("is_superuser", False),
            "is_approved": True,
            "force_password_change": user_def.get("force_password_change", True),
            "totp_secret": None,
            "totp_enabled": False,
            "avatar_url": None,
            "organization_id": user_org_id,
            "created_at": now,
            "updated_at": now,
        }])

        # Assign user to org-scoped groups (not templates)
        for grp in user_def.get("groups", []):
            tid = template_ids.get(grp)
            if not tid or not user_org_id:
                continue
            org_gid = cloned_map.get((tid, user_org_id))
            if org_gid:
                op.bulk_insert(memberships_table, [{
                    "user_id": uid, "group_id": org_gid, "created_at": now,
                }])

    # ── seed: app settings ────────────────────────────────────────────────────
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
    op.drop_table("email_configs")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_codename", table_name="permissions")
    op.drop_table("permissions")
    op.drop_table("user_group_memberships")
    op.drop_index("ix_user_groups_organization_id", table_name="user_groups")
    op.drop_index("uq_user_groups_name_org", table_name="user_groups")
    op.drop_table("user_groups")
    op.drop_index("ix_status_logs_ticket_id", table_name="status_logs")
    op.drop_table("status_logs")
    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_ticket_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_attachments_ticket_id", table_name="attachments")
    op.drop_table("attachments")
    op.drop_index("ix_tickets_organization_id", table_name="tickets")
    op.drop_index("ix_tickets_owner_id", table_name="tickets")
    op.drop_index("ix_tickets_creator_id", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_config_items_type", table_name="config_items")
    op.drop_table("config_items")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_index("ix_organizations_level", table_name="organizations")
    op.drop_table("organizations")
