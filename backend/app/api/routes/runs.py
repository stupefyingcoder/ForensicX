from __future__ import annotations

import asyncio
import json as json_mod
import math
import time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_from_header_or_query, get_db
from app.models.case import Case
from app.models.image import ImageAsset
from app.models.run import Run
from app.models.run_metric import RunMetric
from app.models.run_output import RunOutput
from app.models.user import User
from app.schemas.run import RunCreate, RunResultsOut, RunStatusOut
from app.services.inference_engine import DISCLAIMER
from app.services.jobs import get_run_progress, job_manager


router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunStatusOut)
def create_run(payload: RunCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RunStatusOut:
    case_obj = db.query(Case).filter(Case.id == payload.case_id, Case.user_id == user.id).first()
    if not case_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    image = db.query(ImageAsset).filter(ImageAsset.id == payload.image_id, ImageAsset.case_id == payload.case_id).first()
    if not image:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found in case.")

    config_json = payload.model_dump()
    run = Run(case_id=payload.case_id, status="queued", progress=0, config_json=config_json)
    db.add(run)
    db.commit()
    db.refresh(run)
    job_manager.submit_run(run.id)
    return run


@router.get("/{run_id}", response_model=RunStatusOut)
def get_run_status(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RunStatusOut:
    row = (
        db.query(Run)
        .join(Case, Case.id == Run.case_id)
        .filter(Run.id == run_id, Case.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
    return row


@router.get("/{run_id}/results", response_model=RunResultsOut)
def get_run_results(run_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> RunResultsOut:
    run = (
        db.query(Run)
        .join(Case, Case.id == Run.case_id)
        .filter(Run.id == run_id, Case.user_id == user.id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    outputs = db.query(RunOutput).filter(RunOutput.run_id == run.id).order_by(RunOutput.id.asc()).all()
    metrics = db.query(RunMetric).filter(RunMetric.run_id == run.id).order_by(RunMetric.id.asc()).all()
    for metric in metrics:
        if metric.psnr is not None and not math.isfinite(metric.psnr):
            metric.psnr = None
        if metric.lpips is not None and not math.isfinite(metric.lpips):
            metric.lpips = None
        if metric.ssim is not None and not math.isfinite(metric.ssim):
            metric.ssim = None
    return RunResultsOut(run=run, outputs=outputs, metrics=metrics, disclaimer=DISCLAIMER)


@router.get("/{run_id}/stream")
async def stream_run_progress(
    run_id: int,
    user: User = Depends(get_current_user_from_header_or_query),
    db: Session = Depends(get_db),
):
    """SSE endpoint for real-time run progress."""
    row = (
        db.query(Run)
        .join(Case, Case.id == Run.case_id)
        .filter(Run.id == run_id, Case.user_id == user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    async def event_generator():
        last_progress = -1
        start_time = time.time()
        max_wait = 600  # 10 minutes
        while True:
            progress_data = get_run_progress(run_id)
            if progress_data and progress_data["progress"] != last_progress:
                last_progress = progress_data["progress"]
                yield f"data: {json_mod.dumps(progress_data)}\n\n"
                if progress_data["status"] in ("completed", "failed"):
                    break
            else:
                # Also check DB as fallback
                db_run = db.query(Run).filter(Run.id == run_id).first()
                if db_run and db_run.status in ("completed", "failed"):
                    yield f"data: {json_mod.dumps({'progress': db_run.progress, 'status': db_run.status, 'message': db_run.error_message or 'Done'})}\n\n"
                    break
            if time.time() - start_time > max_wait:
                yield f"data: {json_mod.dumps({'progress': 0, 'status': 'timeout', 'message': 'Stream timed out'})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
