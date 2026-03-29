from datetime import datetime

from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=128)


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_superuser: bool
    groups: list[str] = []
    totp_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_groups(cls, data: Any) -> Any:
        if not hasattr(data, "id"):
            return data
        return {
            "id": data.id,
            "email": data.email,
            "full_name": data.full_name,
            "is_active": data.is_active,
            "is_superuser": data.is_superuser,
            "groups": sorted([group.name for group in data.groups]) if data.groups else [],
            "totp_enabled": data.totp_enabled,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class UserGroupResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class UserGroupUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class UserGroupAssignmentUpdate(BaseModel):
    group_names: list[str] = Field(default_factory=list)


class AssignableUserResponse(BaseModel):
    id: str
    full_name: str

    model_config = {"from_attributes": True}


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_code_url: str
    provisioning_uri: str


class TOTPVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=6)
