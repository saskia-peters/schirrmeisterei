import io
import os
import uuid

import pyotp
import qrcode

from app.core.config import settings


def generate_totp_secret() -> str:
    """Generate a new random base32-encoded TOTP secret."""
    return pyotp.random_base32()


def get_totp_provisioning_uri(secret: str, email: str) -> str:
    """Return an otpauth:// URI for use in QR codes / authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against the given secret, allowing one step of clock drift."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_totp_qr_code_base64(provisioning_uri: str) -> str:
    """Generate a PNG QR code for the given provisioning URI and return it as a base64 data URL."""
    import base64

    img = qrcode.make(provisioning_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return "data:image/png;base64," + base64.b64encode(buffer.read()).decode()


def get_safe_upload_path(upload_dir: str, filename: str) -> str:
    """Generate a safe upload path using UUID to prevent path traversal."""
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{uuid.uuid4()}{ext}"
    return os.path.join(upload_dir, safe_name)
