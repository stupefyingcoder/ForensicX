from __future__ import annotations

import gc
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

from app.core.config import settings
from app.core.logging import logger


@dataclass
class BlurAnalysis:
    """Result of blur detection."""
    laplacian_variance: float
    is_blurry: bool
    blur_level: str  # "low", "medium", "high"


def detect_blur(image: Image.Image, threshold_low: float = 100.0, threshold_high: float = 300.0) -> BlurAnalysis:
    """Detect blur level using Laplacian variance."""
    gray = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2GRAY)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if variance >= threshold_high:
        level = "low"
        is_blurry = False
    elif variance >= threshold_low:
        level = "medium"
        is_blurry = True
    else:
        level = "high"
        is_blurry = True

    return BlurAnalysis(laplacian_variance=variance, is_blurry=is_blurry, blur_level=level)


def _nafnet_deblur(image: Image.Image) -> Image.Image:
    """Run NAFNet deep learning deblurring. Loads model, processes, unloads."""
    from nafnetlib import DeblurProcessor

    # Downscale large images to prevent OOM (NAFNet memory scales with resolution)
    max_dim = 1024
    original_size = image.size
    if image.width > max_dim or image.height > max_dim:
        image = image.copy()
        image.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        logger.info("Downscaled image to %dx%d for NAFNet", image.width, image.height)

    logger.info("Loading NAFNet deblurring model...")
    processor = DeblurProcessor(
        model_id="gopro_width32",
        model_dir=str(settings.ROOT_DIR / "weights" / "nafnet"),
        device=str(settings.MODEL_DEVICE if settings.MODEL_DEVICE != "auto" else "cpu"),
    )
    logger.info("Running NAFNet deblurring...")
    result = processor.process(image)

    # Upscale back to original size if we downscaled
    if result.size != original_size:
        result = result.resize(original_size, Image.Resampling.LANCZOS)

    # Free the model
    del processor
    gc.collect()

    return result


def _opencv_sharpen(image: Image.Image, sharpen_amount: float = 1.5) -> Image.Image:
    """Apply unsharp mask sharpening as a lightweight post-process."""
    img_arr = np.asarray(image, dtype=np.uint8)
    gaussian = cv2.GaussianBlur(img_arr, (0, 0), sigmaX=2.0)
    sharpened = cv2.addWeighted(img_arr, 1.0 + sharpen_amount, gaussian, -sharpen_amount, 0)
    return Image.fromarray(sharpened)


def preprocess_image(
    image: Image.Image,
    mode: str = "auto",
    denoise_strength: int = 10,
    sharpen_amount: float = 1.5,
) -> tuple[Image.Image, dict]:
    """Preprocess image to reduce blur before super-resolution.

    Uses NAFNet (deep learning) for deblurring when mode is "deblur" or "auto" detects blur.
    Falls back to OpenCV sharpening if NAFNet is unavailable.
    """
    metadata: dict = {"mode": mode, "applied": []}

    # Analyze blur
    analysis = detect_blur(image)
    metadata["blur_analysis"] = {
        "laplacian_variance": round(analysis.laplacian_variance, 2),
        "blur_level": analysis.blur_level,
        "is_blurry": analysis.is_blurry,
    }

    # Decide whether to preprocess
    if mode == "none":
        return image, metadata
    if mode == "auto" and not analysis.is_blurry:
        metadata["skipped"] = "Image is sharp enough, no preprocessing needed"
        return image, metadata

    # Stage 1: NAFNet deep deblurring
    try:
        image = _nafnet_deblur(image)
        metadata["applied"].append("nafnet_deblur(gopro_width64)")
    except Exception as e:
        logger.warning("NAFNet deblurring failed, falling back to OpenCV: %s", e)
        # Fallback: OpenCV NLMeans denoising
        img_arr = np.asarray(image, dtype=np.uint8)
        h = max(denoise_strength, 15) if analysis.blur_level == "high" else denoise_strength
        denoised = cv2.fastNlMeansDenoisingColored(img_arr, None, h, h, 7, 21)
        image = Image.fromarray(denoised)
        metadata["applied"].append(f"opencv_nlmeans_fallback(h={h})")

    # Stage 2: Light sharpening post-process
    if sharpen_amount > 0:
        image = _opencv_sharpen(image, sharpen_amount)
        metadata["applied"].append(f"unsharp_mask(amount={sharpen_amount})")

    # Post-analysis
    post_analysis = detect_blur(image)
    metadata["post_blur_analysis"] = {
        "laplacian_variance": round(post_analysis.laplacian_variance, 2),
        "blur_level": post_analysis.blur_level,
        "improvement": round(post_analysis.laplacian_variance - analysis.laplacian_variance, 2),
    }

    return image, metadata
