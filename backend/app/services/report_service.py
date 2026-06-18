from __future__ import annotations

from pathlib import Path
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.experiment import Experiment
from app.storage import export_path


LIMITATION_TEXT = (
    "Limitation: Enhanced images can contain synthesized detail and should be treated as analytical support, "
    "not direct ground-truth evidence reconstruction."
)


def generate_case_report(db: Session, case_obj: Case, title: str) -> Path:
    path = export_path(f"case_{case_obj.id}_report", "md")
    run_count = len(case_obj.runs)
    image_count = len(case_obj.images)
    body = [
        f"# {title}",
        "",
        "## Case Overview",
        f"- Case ID: {case_obj.id}",
        f"- Title: {case_obj.title}",
        f"- Images: {image_count}",
        f"- Runs: {run_count}",
        "",
        "## Model Comparison Notes",
        "- Models used may include SRGAN, Real-ESRGAN x4v3, and bicubic baseline.",
        "- Use PSNR/LPIPS/SSIM plus OCR/face metrics together; do not rely on one metric alone.",
        "",
        "## Limitation",
        LIMITATION_TEXT,
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return path


def generate_experiment_report(db: Session, experiment: Experiment, title: str) -> Path:
    path = export_path(f"experiment_{experiment.id}_report", "md")
    summary = experiment.summary_json or {}
    body = [
        f"# {title}",
        "",
        "## Experiment Overview",
        f"- Experiment ID: {experiment.id}",
        f"- Name: {experiment.name}",
        f"- Dataset: {experiment.dataset_path}",
        f"- Mode: {summary.get('mode')}",
        f"- Rows: {summary.get('rows')}",
        "",
        "## Average Metrics",
        f"- Average PSNR: {summary.get('average_psnr')}",
        f"- Average LPIPS: {summary.get('average_lpips')}",
        "",
        "## Limitation",
        LIMITATION_TEXT,
    ]
    path.write_text("\n".join(body), encoding="utf-8")
    return path

