import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_unrestricted_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
)
from app.db.session import get_db
from app.models.models import RefreshToken, User
from app.schemas.user import (
    AccessToken,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Cookie helpers (S-7) ─────────────────────────────────────────────────────

_REFRESH_COOKIE_NAME = "refresh_token"
# Path scoped to auth endpoints only so the cookie is not sent on every API call.
_REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Attach the refresh token as an HttpOnly cookie (S-7)."""
    response.set_cookie(
        key=_REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path=_REFRESH_COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400,
    )


def _delete_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie on logout (S-7)."""
    response.delete_cookie(
        key=_REFRESH_COOKIE_NAME,
        path=_REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
    )

# ─── JTI helpers ─────────────────────────────────────────────────────────────

async def _store_jti(db: AsyncSession, user_id: str, token: str) -> None:
    """Decode `token`, extract its JTI claim and persist a RefreshToken row (S-4)."""
    payload = decode_token(token)
    if not payload:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    row = RefreshToken(
        jti=jti,
        user_id=user_id,
        expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()


async def _revoke_all_for_user(db: AsyncSession, user_id: str) -> None:
    """Delete every stored refresh token JTI for the given user (S-4)."""
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.flush()


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


@router.post("/login", response_model=AccessToken)
@limiter.limit("10/minute")  # S-5: brute-force guard
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AccessToken:
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
        # S-3: reject replayed codes.  A valid code stays valid for up to
        # 2 × 30 s windows (valid_window=1).  If the same code was already
        # accepted within that window, treat it as a replay attack.
        _TOTP_VALID_WINDOW_SECONDS = 90  # 3 × 30 s (current + 1 drift window + margin)
        if (
            user.last_totp_code == data.totp_code
            and user.last_totp_used_at is not None
            and (datetime.now(timezone.utc) - user.last_totp_used_at)
            < timedelta(seconds=_TOTP_VALID_WINDOW_SECONDS)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code",
            )
        user.last_totp_code = data.totp_code
        user.last_totp_used_at = datetime.now(timezone.utc)
        await db.flush()

    refresh = create_refresh_token(user.id)
    await _store_jti(db, user.id, refresh)  # S-4: persist JTI
    _set_refresh_cookie(response, refresh)   # S-7: HttpOnly cookie
    return AccessToken(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=AccessToken)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> AccessToken:
    """Exchange a valid refresh token cookie for a new access + refresh token pair.

    The refresh token is read from the ``refresh_token`` HttpOnly cookie (S-7).
    The incoming token's JTI is verified against the DB store (S-4) and deleted
    before a new token pair is issued (rotation).  A stolen refresh token that
    has already been rotated will therefore be rejected.
    """
    raw_refresh = request.cookies.get(_REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token cookie",
        )
    payload = decode_token(raw_refresh)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    # S-4: verify JTI exists in DB
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    stored = result.scalar_one_or_none()
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )
    # Rotate: delete old JTI before issuing a new token pair
    await db.delete(stored)
    await db.flush()

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
    new_refresh = create_refresh_token(user.id)
    await _store_jti(db, user.id, new_refresh)  # S-4: persist new JTI
    _set_refresh_cookie(response, new_refresh)   # S-7: rotate cookie
    return AccessToken(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_unrestricted_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/logout")
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_unrestricted_user),
) -> dict[str, str]:
    """Revoke all refresh tokens for the current user and clear the cookie (S-4 / S-7).

    The client is identified by the access token in the ``Authorization`` header.
    All stored JTIs for the user are deleted so any previously issued refresh token
    (e.g. on another device) becomes invalid.  The HttpOnly cookie is also cleared.
    """
    await _revoke_all_for_user(db, current_user.id)
    _delete_refresh_cookie(response)
    return {"message": "Logged out successfully"}


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
@limiter.limit("10/minute")  # S-5
async def verify_totp_endpoint(
    request: Request,
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
    # S-4: revoke all refresh tokens — user must re-authenticate with TOTP
    await _revoke_all_for_user(db, current_user.id)
    return {"message": "TOTP enabled successfully"}


@router.delete("/totp/disable")
@limiter.limit("10/minute")  # S-5
async def disable_totp(
    request: Request,
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
    # S-4: revoke all refresh tokens — user must re-authenticate without TOTP
    await _revoke_all_for_user(db, current_user.id)
    return {"message": "TOTP disabled successfully"}


# ─── Password Recovery (for superadmin) ──────────────────────────────────────

@router.post("/password-reset/request")
@limiter.limit("5/minute")  # S-5: prevent reset-link spam
async def request_password_reset(
    request: Request,
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
