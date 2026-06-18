from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    case_id: int | None = None
    experiment_id: int | None = None
    title: str = Field(default="Forensic Enhancement Report")


class ExportOut(BaseModel):
    id: int
    type: str
    source_id: int
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
