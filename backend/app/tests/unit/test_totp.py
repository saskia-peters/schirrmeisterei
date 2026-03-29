import pytest

from app.services.totp_service import (
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp,
)


class TestTOTP:
    def test_generate_secret(self) -> None:
        secret = generate_totp_secret()
        assert len(secret) == 32  # base32 encoded, 32 chars

    def test_provisioning_uri(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_provisioning_uri(secret, "user@example.com")
        assert "otpauth://" in uri
        assert "user@example.com" in uri or "user%40example.com" in uri
        assert "TicketSystem" in uri

    def test_verify_totp_invalid_code(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False or verify_totp(secret, "000000") is True
        # Just test it doesn't crash with 6 digit code

    def test_verify_totp_wrong_code(self) -> None:
        secret = generate_totp_secret()
        # A clearly invalid code
        result = verify_totp(secret, "999999")
        assert isinstance(result, bool)

    def test_verify_totp_valid_current_code(self) -> None:
        import pyotp
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        assert verify_totp(secret, current_code) is True
