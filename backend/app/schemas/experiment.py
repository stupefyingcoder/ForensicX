from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ExperimentBatchCreate(BaseModel):
    name: str
    dataset_path: str
    mode: str = Field(default="synthetic_x4", pattern="^(synthetic_x4|paired)$")
    models: list[str] = Field(default_factory=lambda: ["srgan", "realesrgan", "bicubic"])
    limit: int | None = Field(default=None, ge=1)
    low_res_dir: str | None = None
    high_res_dir: str | None = None


class ExperimentOut(BaseModel):
    id: int
    name: str
    dataset_path: str
    status: str
    config_json: dict
    summary_json: dict
    csv_path: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
