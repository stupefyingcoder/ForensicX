from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ROI(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class RunCreate(BaseModel):
    case_id: int
    image_id: int
    models: list[str] = Field(default_factory=lambda: ["srgan", "realesrgan", "bicubic"])
    scale: int = Field(default=4, ge=2, le=8)
    roi: ROI | None = None
    reference_image_id: int | None = None
    reference_text: str | None = None
    face_reference_image_id: int | None = None
    preprocess: str = Field(default="auto", pattern="^(auto|deblur|none)$")
    denoise_strength: int = Field(default=10, ge=0, le=30)

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[str]) -> list[str]:
        allowed = {"srgan", "realesrgan", "realesrgan_x4plus", "bsrgan", "bicubic"}
        if len(v) > 10:
            raise ValueError("Too many models specified (max 10).")
        for name in v:
            if name.lower() not in allowed:
                raise ValueError(f"Unknown model '{name}'. Allowed: {', '.join(sorted(allowed))}")
        return v


class RunStatusOut(BaseModel):
    id: int
    case_id: int
    status: str
    progress: int
    config_json: dict
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunOutputOut(BaseModel):
    model_name: str
    output_path: str
    diff_path: str | None
    roi_compare_path: str | None

    model_config = ConfigDict(from_attributes=True)


class RunMetricOut(BaseModel):
    model_name: str
    psnr: float | None
    lpips: float | None
    ssim: float | None
    ocr_json: dict
    face_json: dict

    model_config = ConfigDict(from_attributes=True)


class RunResultsOut(BaseModel):
    run: RunStatusOut
    outputs: list[RunOutputOut]
    metrics: list[RunMetricOut]
    disclaimer: str
