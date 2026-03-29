import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_password(self) -> None:
        hashed = get_password_hash("mypassword")
        assert hashed != "mypassword"
        assert len(hashed) > 0

    def test_verify_correct_password(self) -> None:
        hashed = get_password_hash("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = get_password_hash("mypassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_different_hashes_same_password(self) -> None:
        hash1 = get_password_hash("mypassword")
        hash2 = get_password_hash("mypassword")
        assert hash1 != hash2  # bcrypt uses salt


class TestTokens:
    def test_create_access_token(self) -> None:
        token = create_access_token("user-123")
        assert token is not None
        assert len(token) > 0

    def test_decode_access_token(self) -> None:
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_create_refresh_token(self) -> None:
        token = create_refresh_token("user-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self) -> None:
        payload = decode_token("invalid.token.value")
        assert payload == {}

    def test_access_token_different_from_refresh(self) -> None:
        access = create_access_token("user-123")
        refresh = create_refresh_token("user-123")
        assert access != refresh
