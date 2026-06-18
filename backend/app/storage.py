from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.config import settings


def ensure_storage_dirs() -> None:
    for path in [
        settings.DATA_DIR,
        settings.UPLOAD_DIR,
        settings.RUN_DIR,
        settings.COMPARISON_DIR,
        settings.EXPORT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def new_upload_path(case_id: int, filename: str) -> Path:
    case_dir = settings.UPLOAD_DIR / f"case_{case_id}"
    case_dir.mkdir(parents=True, exist_ok=True)
    import re
    safe_name = re.sub(r"[^\w\-.]", "_", Path(filename).name)
    return case_dir / f"{uuid4().hex}_{safe_name}"


def run_dir(run_id: int) -> Path:
    path = settings.RUN_DIR / f"run_{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def comparison_dir(run_id: int) -> Path:
    path = settings.COMPARISON_DIR / f"run_{run_id}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_path(prefix: str, extension: str) -> Path:
    settings.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return settings.EXPORT_DIR / f"{prefix}_{uuid4().hex}.{extension}"

