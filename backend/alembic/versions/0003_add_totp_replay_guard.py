"""Add TOTP replay-guard columns to users table (S-3)

Stores the last accepted TOTP code and the timestamp it was accepted so that
a second login attempt with the same code within the valid window is rejected.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-13

"""
from collections.abc import Sequence as TypingSequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | TypingSequence[str] | None = None
depends_on: str | TypingSequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_totp_code", sa.String(6), nullable=True),
        schema="ticketsystem",
    )
    op.add_column(
        "users",
        sa.Column("last_totp_used_at", sa.DateTime(timezone=True), nullable=True),
        schema="ticketsystem",
    )


def downgrade() -> None:
    op.drop_column("users", "last_totp_used_at", schema="ticketsystem")
    op.drop_column("users", "last_totp_code", schema="ticketsystem")
