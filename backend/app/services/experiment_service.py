from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from PIL import Image
import torch
import torch.nn.functional as F
import torchvision.transforms as T

from app.services.model_registry import model_cache


def _psnr(a: torch.Tensor, b: torch.Tensor) -> float:
    mse = F.mse_loss(a, b)
    if mse.item() == 0:
        return float("inf")
    return (20 * torch.log10(torch.tensor(1.0, device=a.device) / torch.sqrt(mse))).item()


def _to_model(img: Image.Image, device: torch.device) -> torch.Tensor:
    tensor = T.ToTensor()(img)
    return T.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])(tensor).unsqueeze(0).to(device)


def _to_unit(img: Image.Image, device: torch.device) -> torch.Tensor:
    return T.ToTensor()(img).unsqueeze(0).to(device)


def _lpips_model(device: torch.device):
    import lpips

    model = lpips.LPIPS(net="alex").to(device)
    for p in model.parameters():
        p.requires_grad = False
    return model


def run_batch_benchmark(
    dataset_dir: Path,
    out_csv: Path,
    models: Iterable[str],
    mode: str = "synthetic_x4",
    limit: int | None = None,
    low_res_dir: Path | None = None,
    high_res_dir: Path | None = None,
) -> dict:
    files = sorted([p for p in dataset_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}])
    if limit:
        files = files[:limit]
    if not files and mode == "synthetic_x4":
        raise ValueError(f"No images found in {dataset_dir}")

    # Load srgan first to determine device, then unload — models loaded per-image below
    srgan_model, srgan_device = model_cache.load("srgan")
    metric_device = srgan_device
    model_cache.unload()
    realesr_device = metric_device
    lpips_net = _lpips_model(metric_device)

    model_set = [m.lower() for m in models]
    rows: list[dict] = []

    with torch.no_grad():
        if mode == "paired":
            if not low_res_dir or not high_res_dir:
                raise ValueError("paired mode needs low_res_dir and high_res_dir")
            pairs = []
            for high in sorted(high_res_dir.iterdir()):
                if high.is_file():
                    low = low_res_dir / high.name
                    if low.exists():
                        pairs.append((low, high))
            if limit:
                pairs = pairs[:limit]
            for low_path, high_path in pairs:
                lr = Image.open(low_path).convert("RGB")
                hr = Image.open(high_path).convert("RGB")
                rows.extend(
                    _benchmark_one(
                        file_name=high_path.name,
                        lr=lr,
                        hr=hr,
                        model_set=model_set,
                        lpips_net=lpips_net,
                        metric_device=metric_device,
                    )
                )
        else:
            for hr_path in files:
                hr = Image.open(hr_path).convert("RGB")
                w4, h4 = (hr.width // 4) * 4, (hr.height // 4) * 4
                if w4 == 0 or h4 == 0:
                    continue
                if (w4, h4) != hr.size:
                    hr = hr.crop((0, 0, w4, h4))
                lr = hr.resize((w4 // 4, h4 // 4), Image.Resampling.BICUBIC)
                rows.extend(
                    _benchmark_one(
                        file_name=hr_path.name,
                        lr=lr,
                        hr=hr,
                        model_set=model_set,
                        lpips_net=lpips_net,
                        metric_device=metric_device,
                    )
                )

    if not rows:
        raise ValueError("No benchmark rows were generated.")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    def avg(key: str) -> float:
        vals = [float(r[key]) for r in rows if r[key] is not None]
        return sum(vals) / len(vals) if vals else 0.0

    summary = {
        "rows": len(rows),
        "dataset_dir": str(dataset_dir),
        "mode": mode,
        "models": model_set,
        "average_psnr": {m: avg(f"psnr_{m}") for m in model_set},
        "average_lpips": {m: avg(f"lpips_{m}") for m in model_set},
        "csv_path": str(out_csv),
    }
    return summary


def _benchmark_one(
    file_name: str,
    lr: Image.Image,
    hr: Image.Image,
    model_set: list[str],
    lpips_net,
    metric_device,
) -> list[dict]:
    hr_unit = _to_unit(hr, metric_device)
    hr_model = _to_model(hr, metric_device)
    row = {"file": file_name}

    for model_name in model_set:
        if model_name == "bicubic":
            out_img = lr.resize(hr.size, Image.Resampling.BICUBIC)
            out_unit = _to_unit(out_img, metric_device)
            out_model = _to_model(out_img, metric_device)
        elif model_name == "srgan":
            srgan_model, srgan_device = model_cache.load("srgan")
            try:
                x = _to_model(lr, srgan_device)
                y = srgan_model(x).squeeze(0).detach().cpu().clamp(-1, 1) * 0.5 + 0.5
                out_img = T.ToPILImage()(y)
                out_unit = _to_unit(out_img, metric_device)
                out_model = _to_model(out_img, metric_device)
            finally:
                model_cache.unload()
        elif model_name == "realesrgan":
            realesr_model, realesr_device = model_cache.load("realesrgan")
            try:
                x = _to_unit(lr, realesr_device)
                y = realesr_model(x).squeeze(0).detach().cpu().clamp(0, 1)
                out_img = T.ToPILImage()(y)
                out_unit = _to_unit(out_img, metric_device)
                out_model = _to_model(out_img, metric_device)
            finally:
                model_cache.unload()
        else:
            continue

        row[f"psnr_{model_name}"] = _psnr(out_unit, hr_unit)
        row[f"lpips_{model_name}"] = float(lpips_net(out_model, hr_model).mean().item())

    return [row]

