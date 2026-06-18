from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ImageAssetOut(BaseModel):
    id: int
    case_id: int
    original_path: str
    metadata_json: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: str | None
    created_at: datetime
    images: list[ImageAssetOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
