"""user groups and role assignments

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-29

"""
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_groups",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_groups_name", "user_groups", ["name"], unique=True)

    op.create_table(
        "user_group_memberships",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("group_id", sa.String(36), sa.ForeignKey("user_groups.id"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    now = datetime.now(timezone.utc)
    helfende_id = str(uuid.uuid4())
    schirrmeister_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())

    user_groups_table = sa.table(
        "user_groups",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    memberships_table = sa.table(
        "user_group_memberships",
        sa.column("user_id", sa.String),
        sa.column("group_id", sa.String),
        sa.column("created_at", sa.DateTime),
    )

    op.bulk_insert(
        user_groups_table,
        [
            {"id": helfende_id, "name": "helfende", "created_at": now},
            {"id": schirrmeister_id, "name": "schirrmeister", "created_at": now},
            {"id": admin_id, "name": "admin", "created_at": now},
        ],
    )

    bind = op.get_bind()
    users = list(bind.execute(sa.text("SELECT id, is_superuser FROM users")).mappings())

    rows = []
    for row in users:
        rows.append({"user_id": row["id"], "group_id": helfende_id, "created_at": now})
        if row["is_superuser"]:
            rows.append({"user_id": row["id"], "group_id": admin_id, "created_at": now})

    if rows:
        op.bulk_insert(memberships_table, rows)


def downgrade() -> None:
    op.drop_table("user_group_memberships")
    op.drop_index("ix_user_groups_name", table_name="user_groups")
    op.drop_table("user_groups")
