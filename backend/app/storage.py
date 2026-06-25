from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.config import settings


def resolve_artifact_path(stored_path: str) -> Path | None:
    """Resolve a persisted artifact path to its location under the live DATA_DIR.

    Artifact paths are stored in the DB as absolute paths captured when the file was
    written (e.g. "/app/data_store/runs/run_1/out.png" on the server, or a Windows
    path in local dev). That absolute prefix is unreliable — on Hugging Face Spaces
    the on-disk location of "/app" can change across container rebuilds, and dev/prod
    machines differ. So we ignore the prefix and re-root the part after "data_store"
    under the current DATA_DIR. Returns the resolved Path if it exists, is a file, and
    stays within DATA_DIR, otherwise None.
    """
    allowed_root = settings.DATA_DIR.resolve()
    norm = str(stored_path).replace("\\", "/").strip()
    marker = "data_store/"
    if marker in norm:
        sub = norm.rsplit(marker, 1)[1].lstrip("/")
        candidate = (settings.DATA_DIR / sub).resolve()
    else:
        raw = Path(norm)
        candidate = (raw if raw.is_absolute() else settings.DATA_DIR / raw).resolve()

    if not candidate.is_relative_to(allowed_root):
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


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

