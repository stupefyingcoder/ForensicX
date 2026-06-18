from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path

import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.transforms as T

from app.services.face import face_similarity
from app.services.ocr import run_ocr


def _to_tensor_unit(image: Image.Image, device: torch.device) -> torch.Tensor:
    return T.ToTensor()(image).unsqueeze(0).to(device)


def _to_tensor_model(image: Image.Image, device: torch.device) -> torch.Tensor:
    return T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])(T.ToTensor()(image)).unsqueeze(0).to(device)


def _psnr(pred: torch.Tensor, target: torch.Tensor) -> float:
    mse = F.mse_loss(pred, target)
    if mse.item() == 0:
        return 100.0
    return (20 * torch.log10(torch.tensor(1.0, device=pred.device) / torch.sqrt(mse))).item()


def _json_safe(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _ssim(pred: np.ndarray, target: np.ndarray) -> float | None:
    try:
        from skimage.metrics import structural_similarity
    except Exception:
        return None

    pred_gray = np.asarray(Image.fromarray(pred).convert("L"), dtype=np.float32)
    target_gray = np.asarray(Image.fromarray(target).convert("L"), dtype=np.float32)
    return float(structural_similarity(pred_gray, target_gray, data_range=255))


@lru_cache(maxsize=1)
def _lpips_model(device_name: str):
    import lpips

    model = lpips.LPIPS(net="alex").to(torch.device(device_name))
    for param in model.parameters():
        param.requires_grad = False
    return model


def compute_quality_metrics(
    output_path: Path,
    reference_path: Path | None,
    device: torch.device,
    reference_text: str | None = None,
    face_reference_path: Path | None = None,
) -> dict:
    ocr = run_ocr(str(output_path), reference_text)
    face = face_similarity(str(output_path), str(face_reference_path) if face_reference_path else None)

    if not reference_path:
        return {
            "psnr": None,
            "lpips": None,
            "ssim": None,
            "ocr_json": {
                "available": ocr.available,
                "text": ocr.text,
                "confidence": ocr.confidence,
                "normalized_edit_distance": ocr.normalized_edit_distance,
                "note": ocr.note,
            },
            "face_json": face,
        }

    out_img = Image.open(output_path).convert("RGB")
    ref_img = Image.open(reference_path).convert("RGB")
    if ref_img.size != out_img.size:
        ref_img = ref_img.resize(out_img.size, Image.Resampling.BICUBIC)

    out_unit = _to_tensor_unit(out_img, device)
    ref_unit = _to_tensor_unit(ref_img, device)
    out_model = _to_tensor_model(out_img, device)
    ref_model = _to_tensor_model(ref_img, device)

    psnr_val = _json_safe(_psnr(out_unit, ref_unit))
    ssim_val = _json_safe(
        _ssim(
        (out_unit.squeeze(0).permute(1, 2, 0).detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8),
        (ref_unit.squeeze(0).permute(1, 2, 0).detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8),
        )
    )

    lpips_net = _lpips_model(str(device))
    with torch.no_grad():
        lpips_val = _json_safe(float(lpips_net(out_model, ref_model).mean().item()))

    return {
        "psnr": psnr_val,
        "lpips": lpips_val,
        "ssim": ssim_val,
        "ocr_json": {
            "available": ocr.available,
            "text": ocr.text,
            "confidence": ocr.confidence,
            "normalized_edit_distance": ocr.normalized_edit_distance,
            "note": ocr.note,
        },
        "face_json": face,
    }
