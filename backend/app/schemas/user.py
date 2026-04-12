from datetime import datetime

from typing import Any

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.models import ORG_LEVEL_ABBREV


# ─── Organization Schemas ─────────────────────────────────────────────────────

class OrganizationResponse(BaseModel):
    id: str
    name: str
    level: str
    parent_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationTree(BaseModel):
    id: str
    name: str
    level: str
    children: list["OrganizationTree"] = []


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    organization_id: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=128)


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    organization_id: str
    is_active: bool = True
    group_names: list[str] = Field(default_factory=list)


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=255)
    password: str | None = Field(None, min_length=8, max_length=128)
    is_active: bool | None = None
    organization_id: str | None = None
    group_names: list[str] | None = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_superuser: bool
    is_approved: bool
    force_password_change: bool
    groups: list[str] = []
    totp_enabled: bool
    avatar_url: str | None = None
    organization_id: str | None = None
    organization_name: str | None = None
    organization_level: str | None = None
    org_abbrev: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_groups(cls, data: Any) -> Any:
        if not hasattr(data, "id"):
            return data
        org = getattr(data, "organization", None)
        org_level = org.level.value if org and hasattr(org.level, "value") else (org.level if org else None)
        return {
            "id": data.id,
            "email": data.email,
            "full_name": data.full_name,
            "is_active": data.is_active,
            "is_superuser": data.is_superuser,
            "is_approved": data.is_approved,
            "force_password_change": data.force_password_change,
            "groups": sorted([group.name for group in data.groups]) if data.groups else [],
            "totp_enabled": data.totp_enabled,
            "avatar_url": data.avatar_url,
            "organization_id": data.organization_id,
            "organization_name": org.name if org else None,
            "organization_level": org_level,
            "org_abbrev": ORG_LEVEL_ABBREV.get(org_level, "") if org_level else None,
            "created_at": data.created_at,
            "updated_at": data.updated_at,
        }


class UserGroupResponse(BaseModel):
    id: str
    name: str
    organization_id: str | None = None
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


class AppSettingResponse(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


class AppSettingUpdate(BaseModel):
    value: str = Field(..., min_length=1, max_length=255)


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


# ─── Permission Schemas ───────────────────────────────────────────────────────

class PermissionResponse(BaseModel):
    id: str
    codename: str
    description: str

    model_config = {"from_attributes": True}


class UserGroupDetailResponse(BaseModel):
    id: str
    name: str
    organization_id: str | None = None
    permissions: list[str] = []
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_permissions(cls, data: Any) -> Any:
        if not hasattr(data, "id"):
            return data
        return {
            "id": data.id,
            "name": data.name,
            "organization_id": data.organization_id,
            "permissions": sorted([p.codename for p in data.permissions]) if data.permissions else [],
            "created_at": data.created_at,
        }


class RolePermissionUpdate(BaseModel):
    permission_codenames: list[str] = Field(default_factory=list)


# ─── Email Config Schemas ────────────────────────────────────────────────────

class EmailConfigCreate(BaseModel):
    organization_id: str
    smtp_host: str = Field("", max_length=255)
    smtp_port: int = 587
    smtp_user: str = Field("", max_length=255)
    smtp_password: str = Field("", max_length=255)
    from_email: str = Field("", max_length=255)
    use_tls: bool = True
    is_active: bool = False


class EmailConfigUpdate(BaseModel):
    smtp_host: str | None = Field(None, max_length=255)
    smtp_port: int | None = None
    smtp_user: str | None = Field(None, max_length=255)
    smtp_password: str | None = Field(None, max_length=255)
    from_email: str | None = Field(None, max_length=255)
    use_tls: bool | None = None
    is_active: bool | None = None


class EmailConfigResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: str | None = None
    smtp_host: str
    smtp_port: int
    smtp_user: str
    from_email: str
    use_tls: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def populate_org_name(cls, data: Any) -> Any:
        if hasattr(data, "organization") and data.organization is not None:
            return {
                "id": data.id,
                "organization_id": data.organization_id,
                "organization_name": data.organization.name,
                "smtp_host": data.smtp_host,
                "smtp_port": data.smtp_port,
                "smtp_user": data.smtp_user,
                "from_email": data.from_email,
                "use_tls": data.use_tls,
                "is_active": data.is_active,
                "created_at": data.created_at,
                "updated_at": data.updated_at,
            }
        return data


# ─── Bulk User Upload ────────────────────────────────────────────────────────

class BulkUserUploadResult(BaseModel):
    created: int
    errors: list[str]


# ─── Hierarchy Upload ────────────────────────────────────────────────────────

class HierarchyUploadResult(BaseModel):
    created: int
    skipped: int
    errors: list[str]


# ─── Password Recovery ───────────────────────────────────────────────────────

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)
