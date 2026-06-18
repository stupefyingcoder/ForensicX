from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image
import torch
import torchvision.transforms as T

from app.core.logging import logger
from app.core.config import settings
from app.services.deblur import preprocess_image
from app.services.model_registry import model_cache


DISCLAIMER = (
    "Enhanced outputs are decision-support artifacts and may include synthetic details. "
    "Do not treat generated detail as courtroom-grade reconstruction without independent validation."
)


@dataclass
class ROI:
    x: int
    y: int
    width: int
    height: int


@dataclass
class ModelResult:
    model_name: str
    output_path: Path
    diff_path: Path | None
    roi_compare_path: Path | None


def _srgan_infer(image: Image.Image, model: torch.nn.Module, device: torch.device) -> Image.Image:
    transform = T.Compose([T.ToTensor(), T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])])
    x = transform(image).unsqueeze(0).to(device)
    with torch.no_grad():
        y = model(x).squeeze(0).cpu().clamp(-1, 1) * 0.5 + 0.5
    return T.ToPILImage()(y)


def _realesrgan_infer(image: Image.Image, model: torch.nn.Module, device: torch.device) -> Image.Image:
    x = T.ToTensor()(image).unsqueeze(0).to(device)
    with torch.no_grad():
        y = model(x).squeeze(0).cpu().clamp(0, 1)
    return T.ToPILImage()(y)


def _bicubic_infer(image: Image.Image, scale: int) -> Image.Image:
    return image.resize((image.width * scale, image.height * scale), Image.Resampling.BICUBIC)


def _diff_map(reference: Image.Image, candidate: Image.Image) -> Image.Image:
    if reference.size != candidate.size:
        candidate = candidate.resize(reference.size, Image.Resampling.BICUBIC)
    ref_arr = np.asarray(reference, dtype=np.float32)
    cand_arr = np.asarray(candidate, dtype=np.float32)
    diff = np.abs(cand_arr - ref_arr) * 6.0
    return Image.fromarray(np.clip(diff, 0, 255).astype(np.uint8))


def _clamp_roi(image: Image.Image, roi: ROI | None) -> tuple[int, int, int, int]:
    if roi:
        x1 = max(0, min(image.width - 1, roi.x))
        y1 = max(0, min(image.height - 1, roi.y))
        x2 = max(x1 + 1, min(image.width, x1 + roi.width))
        y2 = max(y1 + 1, min(image.height, y1 + roi.height))
        return x1, y1, x2, y2

    size = min(settings.DEFAULT_ROI_SIZE, image.width, image.height)
    x1 = max(0, (image.width - size) // 2)
    y1 = max(0, (image.height - size) // 2)
    return x1, y1, x1 + size, y1 + size


def _roi_compare(base: Image.Image, candidate: Image.Image, roi: ROI | None) -> Image.Image:
    if base.size != candidate.size:
        candidate = candidate.resize(base.size, Image.Resampling.BICUBIC)
    x1, y1, x2, y2 = _clamp_roi(base, roi)
    crop_a = base.crop((x1, y1, x2, y2))
    crop_b = candidate.crop((x1, y1, x2, y2))
    scale = 3
    crop_a = crop_a.resize((crop_a.width * scale, crop_a.height * scale), Image.Resampling.NEAREST)
    crop_b = crop_b.resize((crop_b.width * scale, crop_b.height * scale), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (crop_a.width * 2, crop_a.height))
    canvas.paste(crop_a, (0, 0))
    canvas.paste(crop_b, (crop_a.width, 0))
    return canvas


def _infer_model(name: str, image: Image.Image) -> Image.Image | None:
    """Load a model, run inference, and unload it. Returns None for bicubic (handled separately)."""
    # For heavy RRDBNet models, cap input smaller to avoid OOM
    infer_image = image
    if name in ("bsrgan", "realesrgan_x4plus"):
        max_dim = 256  # RRDBNet (23 RRDB blocks) needs much less input to stay in memory
        if infer_image.width > max_dim or infer_image.height > max_dim:
            infer_image = infer_image.copy()
            infer_image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    model, device = model_cache.load(name)
    try:
        if name == "srgan":
            return _srgan_infer(infer_image, model, device)
        else:
            return _realesrgan_infer(infer_image, model, device)
    finally:
        model_cache.unload()


def run_models(
    image_path: Path,
    output_dir: Path,
    compare_dir: Path,
    models: Iterable[str],
    scale: int,
    roi: ROI | None,
    preprocess: str = "auto",
    denoise_strength: int = 10,
) -> list[ModelResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    compare_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(image_path).convert("RGB")

    MAX_DIMENSION = 512  # Keep small to avoid OOM — output is 4x this (2048px)
    if image.width > MAX_DIMENSION or image.height > MAX_DIMENSION:
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)

    # Preprocess for blur reduction
    image, preprocess_meta = preprocess_image(image, mode=preprocess, denoise_strength=denoise_strength)
    if preprocess_meta.get("applied"):
        preprocessed_path = output_dir / "preprocessed_input.png"
        image.save(preprocessed_path)

    bicubic = _bicubic_infer(image, scale)
    bicubic_path = output_dir / "bicubic_output.png"
    bicubic.save(bicubic_path)

    results: list[ModelResult] = []
    for model_name in models:
        key = model_name.lower()

        if key == "bicubic":
            out = bicubic
        else:
            try:
                out = _infer_model(key, image)
            except FileNotFoundError as exc:
                logger.warning("Skipping model %s because weights are missing: %s", key, exc)
                continue
            if out is None:
                continue

        out_path = output_dir / f"{key}_output.png"
        out.save(out_path)

        diff = _diff_map(bicubic, out)
        diff_path = compare_dir / f"{key}_diff_vs_bicubic.png"
        diff.save(diff_path)

        roi_cmp = _roi_compare(bicubic, out, roi)
        roi_path = compare_dir / f"{key}_roi_compare.png"
        roi_cmp.save(roi_path)

        results.append(ModelResult(model_name=key, output_path=out_path, diff_path=diff_path, roi_compare_path=roi_path))

    if not results:
        raise RuntimeError("No selected models could run. Install model weights or select Bicubic.")

    return results
