from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.case import Case
from app.models.image import ImageAsset
from app.models.user import User
from app.schemas.case import CaseCreate, CaseOut, ImageAssetOut
from app.storage import new_upload_path


router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseOut)
def create_case(payload: CaseCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseOut:
    case_obj = Case(user_id=user.id, title=payload.title.strip(), description=payload.description)
    db.add(case_obj)
    db.commit()
    db.refresh(case_obj)
    return case_obj


@router.get("", response_model=list[CaseOut])
def list_cases(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CaseOut]:
    rows = db.query(Case).filter(Case.user_id == user.id).order_by(Case.id.desc()).all()
    return rows


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseOut:
    row = db.query(Case).filter(Case.id == case_id, Case.user_id == user.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return row


@router.post("/{case_id}/images", response_model=ImageAssetOut)
def upload_case_image(
    case_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageAssetOut:
    case_obj = db.query(Case).filter(Case.id == case_id, Case.user_id == user.id).first()
    if not case_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    dest = new_upload_path(case_id, file.filename or "uploaded_image.png")
    MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large. Maximum size is 20MB.")
    dest.write_bytes(content)

    try:
        with Image.open(dest) as img:
            width, height = img.size
            mode = img.mode
    except Exception:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is not a valid image.")

    rel_path = str(Path(dest))
    image = ImageAsset(
        case_id=case_id,
        original_path=rel_path,
        metadata_json={"filename": file.filename, "width": width, "height": height, "mode": mode},
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image

