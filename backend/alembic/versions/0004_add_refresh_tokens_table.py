"""Add refresh_tokens JTI store (S-4)

Enables per-token refresh token revocation: every issued refresh token has a
unique JTI persisted here.  Logout and TOTP state changes delete all rows for
the user, forcing full re-authentication.

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-13

"""
from collections.abc import Sequence as TypingSequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | TypingSequence[str] | None = None
depends_on: str | TypingSequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("jti", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("ticketsystem.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        schema="ticketsystem",
    )
    op.create_index(
        "ix_refresh_tokens_user_id",
        "refresh_tokens",
        ["user_id"],
        schema="ticketsystem",
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens", schema="ticketsystem")
    op.drop_table("refresh_tokens", schema="ticketsystem")
