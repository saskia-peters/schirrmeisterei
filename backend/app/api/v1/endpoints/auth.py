import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_unrestricted_user
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
)

logger = logging.getLogger(__name__)
from app.db.session import get_db
from app.models.models import User
from app.schemas.user import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshTokenRequest,
    Token,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    UserCreate,
    UserResponse,
)
from app.services.totp_service import (
    generate_totp_qr_code_base64,
    generate_totp_secret,
    get_totp_provisioning_uri,
    verify_totp,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Register a new user account. Returns 409 if the email is already taken."""
    service = UserService(db)
    existing = await service.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    return await service.create(data)


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Authenticate a user and return a JWT access + refresh token pair."""
    service = UserService(db)
    user = await service.authenticate(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="APPROVAL_PENDING",
        )

    if user.totp_enabled:
        if not data.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="TOTP code required",
            )
        if not user.totp_secret or not verify_totp(user.totp_secret, data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )

    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> Token:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="APPROVAL_PENDING",
        )
    return Token(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_unrestricted_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def setup_totp(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TOTPSetupResponse:
    """Generate a new TOTP secret for the user and return the QR code data URL."""
    secret = generate_totp_secret()
    provisioning_uri = get_totp_provisioning_uri(secret, current_user.email)
    qr_code = generate_totp_qr_code_base64(provisioning_uri)

    service = UserService(db)
    await service.set_totp_secret(current_user, secret)

    return TOTPSetupResponse(
        secret=secret,
        qr_code_url=qr_code,
        provisioning_uri=provisioning_uri,
    )


@router.post("/totp/verify")
async def verify_totp_endpoint(
    data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Verify a TOTP code and permanently enable two-factor authentication for the user."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not set up",
        )
    if not verify_totp(current_user.totp_secret, data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )
    service = UserService(db)
    await service.enable_totp(current_user)
    return {"message": "TOTP enabled successfully"}


@router.delete("/totp/disable")
async def disable_totp(
    data: TOTPVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Disable TOTP for the current user after verifying their code."""
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP not enabled",
        )
    if not verify_totp(current_user.totp_secret, data.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )
    service = UserService(db)
    await service.disable_totp(current_user)
    return {"message": "TOTP disabled successfully"}


# ─── Password Recovery (for superadmin) ──────────────────────────────────────

@router.post("/password-reset/request")
async def request_password_reset(
    data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Request a password reset. Only works for superuser accounts.
    In a real system this would send an email — here we generate a token
    that can be used with the confirm endpoint."""
    service = UserService(db)
    user = await service.get_by_email(data.email)
    # Always return the same message to avoid user enumeration.
    if user and user.is_superuser:
        token = create_password_reset_token(user.id)
        # In production this token would be delivered by email.
        # Log it at DEBUG level so it is available in dev logs without being
        # exposed in the API response (fixes C-1 / A-9).
        logger.debug("Password reset token for %s: %s", data.email, token)
    return {"message": "If the email is registered as a superadmin, a reset link has been sent"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Confirm a password reset using a token."""
    payload = decode_token(data.token)
    if not payload or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if not user or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    from app.schemas.user import UserUpdate
    await service.update(user, UserUpdate(password=data.new_password))
    return {"message": "Password has been reset successfully"}
