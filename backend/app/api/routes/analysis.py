from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.logging import logger
from app.models.analysis import AnalysisRecord
from app.models.case import Case
from app.models.image import ImageAsset
from app.models.user import User
from app.schemas.analysis import AnalysisRequest, AnalysisResult
from app.services.forensic_analysis import run_full_analysis
from app.services.jobs import job_manager, update_run_progress

from PIL import Image


router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("", response_model=AnalysisResult)
def create_analysis(
    payload: AnalysisRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    """Start forensic analysis on an image."""
    case_obj = db.query(Case).filter(Case.id == payload.case_id, Case.user_id == user.id).first()
    if not case_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    image_obj = db.query(ImageAsset).filter(
        ImageAsset.id == payload.image_id, ImageAsset.case_id == payload.case_id
    ).first()
    if not image_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found in case.")

    record = AnalysisRecord(
        case_id=payload.case_id,
        image_id=payload.image_id,
        status="queued",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Run analysis in background thread
    job_manager.executor.submit(_run_analysis_job, record.id, image_obj.original_path)
    return record


@router.get("/{analysis_id}", response_model=AnalysisResult)
def get_analysis(
    analysis_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResult:
    """Get analysis results."""
    record = (
        db.query(AnalysisRecord)
        .join(Case, Case.id == AnalysisRecord.case_id)
        .filter(AnalysisRecord.id == analysis_id, Case.user_id == user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return record


def _run_analysis_job(record_id: int, image_path: str) -> None:
    """Background job for forensic analysis."""
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
        if not record:
            return

        record.status = "running"
        db.commit()

        # Create output directory for analysis artifacts
        output_dir = settings.DATA_DIR / "analysis" / str(record_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        image = Image.open(image_path).convert("RGB")
        results = run_full_analysis(image, file_path=Path(image_path), output_dir=output_dir)

        record.results_json = results
        record.status = "completed"
        record.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Analysis %d completed", record_id)

    except Exception as exc:
        logger.exception("Analysis %d failed", record_id)
        record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
        if record:
            record.status = "failed"
            record.error_message = "Analysis failed. Check server logs for details."
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
