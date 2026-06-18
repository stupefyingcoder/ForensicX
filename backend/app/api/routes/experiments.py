from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.experiment import Experiment
from app.models.user import User
from app.schemas.experiment import ExperimentBatchCreate, ExperimentOut
from app.services.jobs import job_manager


router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/batch", response_model=ExperimentOut)
def create_batch_experiment(
    payload: ExperimentBatchCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExperimentOut:
    exp = Experiment(
        name=payload.name,
        dataset_path=payload.dataset_path,
        status="queued",
        config_json=payload.model_dump(),
        summary_json={},
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    job_manager.submit_experiment(exp.id)
    return exp


@router.get("/{experiment_id}/summary", response_model=ExperimentOut)
def get_experiment_summary(experiment_id: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ExperimentOut:
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found.")
    return exp


@router.get("/{experiment_id}/csv")
def get_experiment_csv(
    experiment_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found.")
    if not exp.csv_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CSV not generated yet.")
    path = Path(exp.csv_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CSV file missing on disk.")
    return FileResponse(path, filename=path.name, media_type="text/csv")
