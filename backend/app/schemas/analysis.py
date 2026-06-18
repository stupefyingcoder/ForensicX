from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AnalysisRequest(BaseModel):
    case_id: int
    image_id: int


class AnalysisResult(BaseModel):
    id: int
    case_id: int
    image_id: int
    status: str
    results_json: dict | None = None
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)
