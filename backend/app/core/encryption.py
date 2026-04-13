"""At-rest encryption for sensitive DB columns (S-6).

Provides ``EncryptedString``, a SQLAlchemy ``TypeDecorator`` that
transparently encrypts on write and decrypts on read using **Fernet**
(AES-128-CBC + HMAC-SHA256).  The encryption key is derived from
``settings.SECRET_KEY`` via **HKDF-SHA256** so rotating the app secret
automatically invalidates stored ciphertext.

Usage::

    from app.core.encryption import EncryptedString

    class MyModel(Base):
        secret_col: Mapped[str] = mapped_column(EncryptedString, nullable=False)

Upgrade note (SCALE-UP): at Tier-3+ consider migrating to a dedicated KMS
(AWS KMS, GCP Cloud KMS) so that the encryption key is not co-located with
the application data.  The only change needed is swapping ``_get_fernet()``
for a KMS client call — the TypeDecorator interface stays identical.
"""

import base64
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a URL-safe base64-encoded 32-byte Fernet key from *secret* via HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"ticketsystem:smtp_password_v1",
    )
    return base64.urlsafe_b64encode(hkdf.derive(secret.encode()))


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Return a lazily-initialised, cached ``Fernet`` instance (key from settings)."""
    from app.core.config import settings  # lazy import — avoids circular dependency

    return Fernet(_derive_fernet_key(settings.SECRET_KEY))


class EncryptedString(TypeDecorator[str]):
    """Fernet-encrypted TEXT column.  Encryption is transparent to callers.

    * Empty strings and ``None`` are stored as-is (column default/null semantics
      are preserved and no Fernet overhead is incurred for unset fields).
    * On read, a value that cannot be decrypted (e.g. plaintext left by a
      pre-migration row that the data migration missed) is returned as-is so
      that the application does not crash; an admin update will re-encrypt it.
    """

    impl = Text  # underlying DB type — Text accommodates the ~200-char ciphertext
    cache_ok = True  # safe: all instances share the same derived key

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        """Encrypt plaintext *value* before persisting to the database."""
        if not value:
            return value
        return _get_fernet().encrypt(value.encode()).decode()

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        """Decrypt *value* read from the database."""
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except Exception:
            # Pre-migration plaintext or data written with a different key.
            # Return as-is; the next save will re-encrypt with the current key.
            return value
