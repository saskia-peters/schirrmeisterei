"""ticket_watchers table

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ticket_watchers",
        sa.Column("ticket_id", sa.String(36), sa.ForeignKey("tickets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_ticket_watchers_ticket_id", "ticket_watchers", ["ticket_id"])
    op.create_index("ix_ticket_watchers_user_id", "ticket_watchers", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_ticket_watchers_user_id", table_name="ticket_watchers")
    op.drop_index("ix_ticket_watchers_ticket_id", table_name="ticket_watchers")
    op.drop_table("ticket_watchers")
