from datetime import datetime

from pydantic import BaseModel, Field

from app.models.models import ConfigItemType


class ConfigItemCreate(BaseModel):
    type: ConfigItemType
    name: str = Field(..., min_length=1, max_length=255)
    sort_order: int = 0


class ConfigItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sort_order: int | None = None
    is_active: bool | None = None


class ConfigItemResponse(BaseModel):
    id: str
    type: ConfigItemType
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
