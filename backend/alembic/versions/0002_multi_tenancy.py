"""multi-tenancy: organizations, permissions, email config

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-05

"""
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

import bcrypt
import sqlalchemy as sa
import yaml
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
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
        sa.Column("organization_id", sa.String(36), sa.ForeignKey("organizations.id"),
                  nullable=False, unique=True),
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

    # ── add organization_id to users ──────────────────────────────────────────
    op.add_column("users", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_users_organization_id", "users", "organizations",
        ["organization_id"], ["id"]
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    # ── add organization_id to tickets ────────────────────────────────────────
    op.add_column("tickets", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        "fk_tickets_organization_id", "tickets", "organizations",
        ["organization_id"], ["id"]
    )
    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"])

    # ══════════════════════════════════════════════════════════════════════════
    # SEED DATA
    # ══════════════════════════════════════════════════════════════════════════

    # ── seed: organizations from YAML ─────────────────────────────────────────
    seed_orgs = _load_seed("organisations.yaml")
    org_ids: dict[str, str] = {}  # name -> id

    for entry in seed_orgs.get("hierarchy", []):
        oid = str(uuid.uuid4())
        org_ids[entry["name"]] = oid
        conn = op.get_bind()
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

    # ── seed: permissions ─────────────────────────────────────────────────────
    seed_perms = _load_seed("permissions.yaml")
    perm_ids: dict[str, str] = {}
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

    # ── seed: role_permissions ────────────────────────────────────────────────
    seed_rp = _load_seed("role_permissions.yaml")
    conn = op.get_bind()
    role_rows = conn.execute(sa.text("SELECT id, name FROM user_groups")).fetchall()
    role_ids: dict[str, str] = {row[1]: row[0] for row in role_rows}

    rp_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    for role_name, perm_codenames in seed_rp.get("role_permissions", {}).items():
        rid = role_ids.get(role_name)
        if not rid:
            continue
        for codename in perm_codenames:
            pid = perm_ids.get(codename)
            if not pid:
                continue
            op.bulk_insert(rp_table, [{"role_id": rid, "permission_id": pid, "created_at": now}])

    # ── seed: assign existing superusers to the Leitung org ───────────────────
    leitung_id = org_ids.get("THW-Leitung")
    if leitung_id:
        conn.execute(
            sa.text("UPDATE users SET organization_id = :org_id WHERE is_superuser = true"),
            {"org_id": leitung_id},
        )

    # ── seed: additional admin users with organization (created post-0002) ─────
    seed_users = _load_seed("admin_users.yaml")
    org_users = [u for u in seed_users.get("users", []) if u.get("organization")]

    users_t = sa.table(
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
        sa.column("organization_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    memberships_t = sa.table(
        "user_group_memberships",
        sa.column("user_id", sa.String),
        sa.column("group_id", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    for user_def in org_users:
        # Skip if email already exists (e.g. created by a prior migration run)
        existing = conn.execute(
            sa.text("SELECT id FROM users WHERE email = :email"),
            {"email": user_def["email"]},
        ).fetchone()
        if existing:
            continue

        uid = str(uuid.uuid4())
        hashed = bcrypt.hashpw(user_def["password"].encode(), bcrypt.gensalt()).decode()
        org_id = org_ids.get(user_def.get("organization", ""))
        op.bulk_insert(users_t, [{
            "id": uid,
            "email": user_def["email"],
            "hashed_password": hashed,
            "full_name": user_def["full_name"],
            "is_active": True,
            "is_superuser": user_def.get("is_superuser", False),
            "force_password_change": user_def.get("force_password_change", True),
            "totp_secret": None,
            "totp_enabled": False,
            "organization_id": org_id,
            "created_at": now,
            "updated_at": now,
        }])
        membership_rows = []
        for grp in user_def.get("groups", []):
            gid = role_ids.get(grp)
            if gid:
                membership_rows.append({"user_id": uid, "group_id": gid, "created_at": now})
        if membership_rows:
            op.bulk_insert(memberships_t, membership_rows)


def downgrade() -> None:
    op.drop_index("ix_tickets_organization_id", table_name="tickets")
    op.drop_constraint("fk_tickets_organization_id", "tickets", type_="foreignkey")
    op.drop_column("tickets", "organization_id")

    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_column("users", "organization_id")

    op.drop_table("email_configs")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_codename", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_index("ix_organizations_level", table_name="organizations")
    op.drop_table("organizations")
