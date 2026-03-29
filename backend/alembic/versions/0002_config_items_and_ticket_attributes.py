"""config_items and ticket attributes

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-29

"""
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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

    # SQLite cannot ALTER constraints directly; batch mode recreates the table safely.
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.add_column(sa.Column("priority_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("category_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("affected_group_id", sa.String(36), nullable=True))

        batch_op.create_foreign_key(
            "fk_tickets_priority_id_config_items",
            "config_items",
            ["priority_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_tickets_category_id_config_items",
            "config_items",
            ["category_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_tickets_affected_group_id_config_items",
            "config_items",
            ["affected_group_id"],
            ["id"],
        )

    # Seed default priorities
    now = datetime.now(timezone.utc)
    config_items_table = sa.table(
        "config_items",
        sa.column("id", sa.String),
        sa.column("type", sa.String),
        sa.column("name", sa.String),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    op.bulk_insert(
        config_items_table,
        [
            {"id": str(uuid.uuid4()), "type": "priority", "name": "Kritisch", "sort_order": 0, "is_active": True, "created_at": now},
            {"id": str(uuid.uuid4()), "type": "priority", "name": "Hoch", "sort_order": 1, "is_active": True, "created_at": now},
            {"id": str(uuid.uuid4()), "type": "priority", "name": "Mittel", "sort_order": 2, "is_active": True, "created_at": now},
            {"id": str(uuid.uuid4()), "type": "priority", "name": "Gering", "sort_order": 3, "is_active": True, "created_at": now},
        ],
    )


def downgrade() -> None:
    with op.batch_alter_table("tickets") as batch_op:
        batch_op.drop_constraint("fk_tickets_affected_group_id_config_items", type_="foreignkey")
        batch_op.drop_constraint("fk_tickets_category_id_config_items", type_="foreignkey")
        batch_op.drop_constraint("fk_tickets_priority_id_config_items", type_="foreignkey")
        batch_op.drop_column("affected_group_id")
        batch_op.drop_column("category_id")
        batch_op.drop_column("priority_id")
    op.drop_index("ix_config_items_type", "config_items")
    op.drop_table("config_items")
    op.execute("DROP TYPE IF EXISTS configitemtype")
