"""add ticket_number auto-increment column

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-12

"""
from collections.abc import Sequence as TypingSequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | TypingSequence[str] | None = None
depends_on: str | TypingSequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS ticketsystem.ticket_number_seq")
    op.add_column(
        "tickets",
        sa.Column(
            "ticket_number",
            sa.Integer(),
            server_default=sa.text("nextval('ticketsystem.ticket_number_seq')"),
            nullable=False,
        ),
    )
    op.create_unique_constraint("uq_tickets_ticket_number", "tickets", ["ticket_number"])


def downgrade() -> None:
    op.drop_constraint("uq_tickets_ticket_number", "tickets", type_="unique")
    op.drop_column("tickets", "ticket_number")
    op.execute("DROP SEQUENCE IF EXISTS ticketsystem.ticket_number_seq")
