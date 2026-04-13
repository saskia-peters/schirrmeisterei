"""Encrypt smtp_password column at rest using Fernet (S-6)

Widens ``email_configs.smtp_password`` from ``VARCHAR(255)`` to ``TEXT``
(Fernet ciphertext is ~200 chars for typical passwords) and encrypts every
existing plaintext value using the same HKDF-derived key that the
``EncryptedString`` TypeDecorator uses at runtime.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-13

"""

from collections.abc import Sequence as TypingSequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | TypingSequence[str] | None = None
depends_on: str | TypingSequence[str] | None = None


def upgrade() -> None:
    # 1. Widen the column to TEXT so ciphertext (≈200 chars) fits.
    op.alter_column(
        "email_configs",
        "smtp_password",
        existing_type=sa.String(255),
        type_=sa.Text,
        existing_nullable=False,
        schema="ticketsystem",
    )

    # 2. Encrypt every non-empty plaintext value that is already in the DB.
    #    op.get_bind() returns the synchronous Connection (Alembic runs migrations
    #    inside connection.run_sync() so this is always a sync connection).
    from app.core.encryption import _get_fernet  # noqa: PLC0415

    fernet = _get_fernet()
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, smtp_password FROM ticketsystem.email_configs")
    ).fetchall()
    for row_id, plaintext in rows:
        if plaintext:
            encrypted = fernet.encrypt(plaintext.encode()).decode()
            bind.execute(
                sa.text(
                    "UPDATE ticketsystem.email_configs"
                    " SET smtp_password = :enc WHERE id = :id"
                ),
                {"enc": encrypted, "id": row_id},
            )


def downgrade() -> None:
    # 1. Decrypt every encrypted value back to plaintext.
    from app.core.encryption import _get_fernet  # noqa: PLC0415

    fernet = _get_fernet()
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, smtp_password FROM ticketsystem.email_configs")
    ).fetchall()
    for row_id, ciphertext in rows:
        if ciphertext:
            try:
                plaintext = fernet.decrypt(ciphertext.encode()).decode()
            except Exception:
                plaintext = ciphertext  # already plaintext (shouldn't happen)
            bind.execute(
                sa.text(
                    "UPDATE ticketsystem.email_configs"
                    " SET smtp_password = :plain WHERE id = :id"
                ),
                {"plain": plaintext, "id": row_id},
            )

    # 2. Narrow the column back to VARCHAR(255).
    op.alter_column(
        "email_configs",
        "smtp_password",
        existing_type=sa.Text,
        type_=sa.String(255),
        existing_nullable=False,
        schema="ticketsystem",
    )
