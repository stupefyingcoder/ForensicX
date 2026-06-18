from __future__ import annotations

import os
from pathlib import Path


class Settings:
    APP_NAME = "Forensic Enhancement Web App"
    API_PREFIX = "/api"

    ROOT_DIR = Path(__file__).resolve().parents[2]
    DATA_DIR = ROOT_DIR / "data_store"
    UPLOAD_DIR = DATA_DIR / "uploads"
    RUN_DIR = DATA_DIR / "runs"
    COMPARISON_DIR = DATA_DIR / "comparisons"
    EXPORT_DIR = DATA_DIR / "exports"

    SQLITE_PATH = ROOT_DIR / "forensic_app.db"
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH.as_posix()}")

    JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))

    MODEL_DEVICE = os.getenv("MODEL_DEVICE", "auto")
    SRGAN_WEIGHTS = ROOT_DIR / "weights" / "srgan_generator.pth"
    REALESRGAN_X4_WEIGHTS = ROOT_DIR / "weights" / "realesr-general-x4v3.pth"
    REALESRGAN_WDN_X4_WEIGHTS = ROOT_DIR / "weights" / "realesr-general-wdn-x4v3.pth"
    REALESRGAN_X4PLUS_WEIGHTS = ROOT_DIR / "weights" / "RealESRGAN_x4plus.pth"
    BSRGAN_WEIGHTS = ROOT_DIR / "weights" / "BSRGAN.pth"
    DENOISE_STRENGTH = float(os.getenv("DENOISE_STRENGTH", "0.5"))

    DEFAULT_ROI_SIZE = int(os.getenv("DEFAULT_ROI_SIZE", "256"))
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", "1"))
    ALLOWED_ORIGINS: list[str] = [
        o.strip() for o in os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
        ).split(",") if o.strip()
    ]


settings = Settings()

if settings.JWT_SECRET == "change-this-in-production":
    import warnings
    warnings.warn(
        "JWT_SECRET is using the default value. Set JWT_SECRET environment variable for production.",
        stacklevel=1,
    )
