from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.experiment import Experiment
from app.models.image import ImageAsset
from app.models.run import Run
from app.models.run_metric import RunMetric
from app.models.run_output import RunOutput
from app.schemas.run import ROI
from app.services.experiment_service import run_batch_benchmark
from app.services.inference_engine import run_models
from app.services.metrics import compute_quality_metrics
from app.services.model_registry import resolve_device
from app.core.logging import logger
from app.storage import comparison_dir, run_dir


# In-memory progress store: {run_id: {"progress": int, "status": str, "message": str}}
_run_progress: dict[int, dict[str, Any]] = {}
_progress_lock = threading.Lock()


def update_run_progress(run_id: int, progress: int, status: str, message: str = "") -> None:
    with _progress_lock:
        _run_progress[run_id] = {"progress": progress, "status": status, "message": message}


def get_run_progress(run_id: int) -> dict[str, Any] | None:
    with _progress_lock:
        return _run_progress.get(run_id, None)


def clear_run_progress(run_id: int) -> None:
    with _progress_lock:
        _run_progress.pop(run_id, None)


class JobManager:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)

    def submit_run(self, run_id: int) -> None:
        self.executor.submit(self._run_job, run_id)

    def submit_experiment(self, experiment_id: int) -> None:
        self.executor.submit(self._experiment_job, experiment_id)

    def _run_job(self, run_id: int) -> None:
        db = SessionLocal()
        try:
            run = db.query(Run).filter(Run.id == run_id).first()
            if not run:
                return
            run.status = "running"
            logger.info("Run %d started", run_id)
            run.started_at = datetime.now(timezone.utc)
            run.progress = 5
            db.commit()
            update_run_progress(run_id, 5, "running", "Loading image")

            cfg: dict[str, Any] = run.config_json or {}
            image = db.query(ImageAsset).filter(ImageAsset.id == cfg.get("image_id")).first()
            if not image:
                raise ValueError("Input image not found for run.")

            roi_obj = None
            roi_cfg = cfg.get("roi")
            if isinstance(roi_cfg, dict):
                roi_obj = ROI(**roi_cfg)

            output_root = run_dir(run.id)
            compare_root = comparison_dir(run.id)
            model_list = [m.lower() for m in cfg.get("models", ["srgan", "realesrgan", "bicubic"])]
            results = run_models(
                image_path=Path(image.original_path),
                output_dir=output_root,
                compare_dir=compare_root,
                models=model_list,
                scale=int(cfg.get("scale", 4)),
                roi=roi_obj,
                preprocess=str(cfg.get("preprocess", "auto")),
                denoise_strength=int(cfg.get("denoise_strength", 10)),
            )
            run.progress = 60
            db.commit()
            update_run_progress(run_id, 60, "running", "Models complete, computing metrics")

            reference_img = None
            reference_id = cfg.get("reference_image_id")
            if reference_id:
                ref_obj = db.query(ImageAsset).filter(ImageAsset.id == reference_id).first()
                if ref_obj:
                    reference_img = Path(ref_obj.original_path)

            face_reference = None
            face_ref_id = cfg.get("face_reference_image_id")
            if face_ref_id:
                face_obj = db.query(ImageAsset).filter(ImageAsset.id == face_ref_id).first()
                if face_obj:
                    face_reference = Path(face_obj.original_path)

            for idx, item in enumerate(results, 1):
                db.add(
                    RunOutput(
                        run_id=run.id,
                        model_name=item.model_name,
                        output_path=str(item.output_path),
                        diff_path=str(item.diff_path) if item.diff_path else None,
                        roi_compare_path=str(item.roi_compare_path) if item.roi_compare_path else None,
                    )
                )

                metric = compute_quality_metrics(
                    output_path=item.output_path,
                    reference_path=reference_img,
                    device=resolve_device(),
                    reference_text=cfg.get("reference_text"),
                    face_reference_path=face_reference,
                )
                db.add(
                    RunMetric(
                        run_id=run.id,
                        model_name=item.model_name,
                        psnr=metric["psnr"],
                        lpips=metric["lpips"],
                        ssim=metric["ssim"],
                        ocr_json=metric["ocr_json"],
                        face_json=metric["face_json"],
                    )
                )
                run.progress = 60 + int(35 * idx / max(len(results), 1))
                db.commit()
                update_run_progress(run_id, run.progress, "running", f"Metrics for {item.model_name}")

            run.status = "completed"
            logger.info("Run %d completed", run_id)
            run.progress = 100
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            update_run_progress(run_id, 100, "completed", "Done")
        except Exception as exc:
            logger.exception("Run %d failed", run_id)
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.status = "failed"
                run.error_message = "Enhancement failed. Check server logs for details."
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                update_run_progress(run_id, run.progress if run else 0, "failed", "Enhancement failed. Check server logs for details.")
        finally:
            db.close()

    def _experiment_job(self, experiment_id: int) -> None:
        db = SessionLocal()
        try:
            exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
            if not exp:
                return
            exp.status = "running"
            db.commit()

            cfg = exp.config_json or {}
            out_csv = Path(settings.EXPORT_DIR) / f"experiment_{exp.id}_results.csv"
            summary = run_batch_benchmark(
                dataset_dir=Path(exp.dataset_path),
                out_csv=out_csv,
                models=cfg.get("models", ["srgan", "realesrgan", "bicubic"]),
                mode=cfg.get("mode", "synthetic_x4"),
                limit=cfg.get("limit"),
                low_res_dir=Path(cfg["low_res_dir"]) if cfg.get("low_res_dir") else None,
                high_res_dir=Path(cfg["high_res_dir"]) if cfg.get("high_res_dir") else None,
            )
            exp.summary_json = summary
            exp.csv_path = str(out_csv)
            exp.status = "completed"
            exp.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
            if exp:
                exp.status = "failed"
                exp.error_message = "Enhancement failed. Check server logs for details."
                exp.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()


job_manager = JobManager()
