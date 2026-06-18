from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user_from_header_or_query
from app.core.config import settings
from app.models.user import User


router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
def get_file(
    path: str = Query(..., description="Absolute or app-relative path for a generated artifact."),
    _: User = Depends(get_current_user_from_header_or_query),
):
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (settings.DATA_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()

    allowed_root = settings.DATA_DIR.resolve()
    if not candidate.is_relative_to(allowed_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path is outside allowed scope.")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return FileResponse(candidate, filename=candidate.name)
