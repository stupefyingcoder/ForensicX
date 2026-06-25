from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.deps import get_current_user_from_header_or_query
from app.models.user import User
from app.storage import resolve_artifact_path


router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
def get_file(
    path: str = Query(..., description="Artifact path (absolute, app-relative, or data_store-relative)."),
    _: User = Depends(get_current_user_from_header_or_query),
):
    candidate = resolve_artifact_path(path)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return FileResponse(candidate, filename=candidate.name)
