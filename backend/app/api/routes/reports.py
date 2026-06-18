from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.case import Case
from app.models.export import Export
from app.models.experiment import Experiment
from app.models.user import User
from app.schemas.report import ExportOut, ReportGenerateRequest
from app.services.report_service import generate_case_report, generate_experiment_report


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ExportOut)
def generate_report(
    payload: ReportGenerateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportOut:
    if payload.case_id is None and payload.experiment_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide case_id or experiment_id.")

    if payload.case_id is not None:
        case_obj = db.query(Case).filter(Case.id == payload.case_id, Case.user_id == user.id).first()
        if not case_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
        report_path = generate_case_report(db, case_obj, payload.title)
        export = Export(type="case_report", source_id=case_obj.id, file_path=str(report_path))
    else:
        exp = db.query(Experiment).filter(Experiment.id == payload.experiment_id).first()
        if not exp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found.")
        report_path = generate_experiment_report(db, exp, payload.title)
        export = Export(type="experiment_report", source_id=exp.id, file_path=str(report_path))

    db.add(export)
    db.commit()
    db.refresh(export)
    return export


@router.get("/{export_id}")
def get_report(
    export_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    export = db.query(Export).filter(Export.id == export_id).first()
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report export not found.")
    path = Path(export.file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file missing.")
    media_type = "text/markdown" if path.suffix.lower() == ".md" else "text/plain"
    return FileResponse(path, filename=path.name, media_type=media_type)
