from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

from app.core.logging import logger


# ---------------------------------------------------------------------------
# 1. Error Level Analysis (ELA)
# ---------------------------------------------------------------------------

def error_level_analysis(
    image: Image.Image,
    quality: int = 90,
    amplification: int = 15,
) -> tuple[Image.Image, dict]:
    """Detect tampering by comparing JPEG compression error levels.

    Resaves the image at a known JPEG quality, then computes the pixel-level
    difference. Manipulated regions compress differently and show higher
    error levels (brighter in the output).

    Args:
        image: Input PIL image.
        quality: JPEG resave quality (lower = more aggressive, 90 is standard).
        amplification: Multiplier for the error map visibility.

    Returns:
        (ela_image, metadata) — the ELA heatmap and analysis stats.
    """
    # Resave at known quality
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer).convert("RGB")

    # Compute difference
    original_arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    resaved_arr = np.asarray(resaved, dtype=np.float32)
    diff = np.abs(original_arr - resaved_arr) * amplification
    ela_arr = np.clip(diff, 0, 255).astype(np.uint8)

    # Statistics
    mean_error = float(np.mean(diff))
    max_error = float(np.max(diff))
    std_error = float(np.std(diff))

    # Suspicious region detection: areas with error > 2 standard deviations
    threshold = mean_error + 2 * std_error
    suspicious_pixels = int(np.sum(np.mean(diff, axis=2) > threshold))
    total_pixels = ela_arr.shape[0] * ela_arr.shape[1]
    suspicious_ratio = suspicious_pixels / total_pixels if total_pixels > 0 else 0

    # Verdict
    if suspicious_ratio > 0.05:
        verdict = "Potential tampering detected — significant ELA inconsistencies"
    elif suspicious_ratio > 0.01:
        verdict = "Minor ELA inconsistencies — review flagged regions"
    else:
        verdict = "No significant ELA anomalies detected"

    metadata = {
        "quality": quality,
        "amplification": amplification,
        "mean_error": round(mean_error, 2),
        "max_error": round(max_error, 2),
        "std_error": round(std_error, 2),
        "suspicious_pixel_ratio": round(suspicious_ratio, 4),
        "verdict": verdict,
    }

    return Image.fromarray(ela_arr), metadata


# ---------------------------------------------------------------------------
# 2. Metadata / EXIF Analysis
# ---------------------------------------------------------------------------

def extract_metadata(image: Image.Image, file_path: Path | None = None) -> dict:
    """Extract and analyze image metadata for authenticity indicators.

    Checks EXIF data for editing software, timestamps, GPS, camera info,
    and flags potential inconsistencies.
    """
    result: dict = {
        "format": image.format or "Unknown",
        "mode": image.mode,
        "size": {"width": image.width, "height": image.height},
        "exif": {},
        "flags": [],
    }

    # File-level info
    if file_path and file_path.exists():
        stat = file_path.stat()
        result["file"] = {
            "name": file_path.name,
            "size_bytes": stat.st_size,
        }

    # Extract EXIF
    exif_data = image.getexif()
    if not exif_data:
        result["flags"].append("No EXIF data found — may have been stripped (common in edited images)")
        return result

    parsed_exif: dict = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))
        try:
            if isinstance(value, bytes):
                parsed_exif[tag_name] = value.hex()[:100]
            else:
                parsed_exif[tag_name] = str(value)
        except Exception:
            parsed_exif[tag_name] = "<unreadable>"

    result["exif"] = parsed_exif

    # Flag analysis
    software = parsed_exif.get("Software", "").lower()
    editing_tools = ["photoshop", "gimp", "lightroom", "snapseed", "pixlr", "canva", "affinity"]
    for tool in editing_tools:
        if tool in software:
            result["flags"].append(f"Editing software detected: {parsed_exif.get('Software')}")
            break

    if "DateTime" not in parsed_exif and "DateTimeOriginal" not in parsed_exif:
        result["flags"].append("No timestamp in metadata — unusual for camera photos")

    if "Make" not in parsed_exif and "Model" not in parsed_exif:
        result["flags"].append("No camera make/model — image may be synthetic or heavily processed")

    # GPS extraction
    gps_ifd = exif_data.get_ifd(0x8825)
    if gps_ifd:
        gps_info = {}
        for gps_tag_id, gps_value in gps_ifd.items():
            gps_tag_name = GPSTAGS.get(gps_tag_id, str(gps_tag_id))
            gps_info[gps_tag_name] = str(gps_value)
        result["gps"] = gps_info
    else:
        result["flags"].append("No GPS data found")

    if not result["flags"]:
        result["flags"].append("Metadata appears consistent — no anomalies detected")

    return result


# ---------------------------------------------------------------------------
# 3. Copy-Move Forgery Detection
# ---------------------------------------------------------------------------

def detect_copy_move(
    image: Image.Image,
    min_matches: int = 10,
    distance_threshold: float = 30.0,
) -> tuple[Image.Image, dict]:
    """Detect copy-move forgery using ORB feature matching.

    Finds regions that have been duplicated (copied and pasted) within the
    same image — a common tampering technique.

    Args:
        image: Input PIL image.
        min_matches: Minimum feature matches to flag as suspicious.
        distance_threshold: Minimum pixel distance between matched points
            to count as a copy-move (filters out self-matches).

    Returns:
        (annotated_image, metadata) — image with matched regions drawn, and stats.
    """
    img_arr = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(img_arr, cv2.COLOR_RGB2GRAY)

    # ORB feature detection
    orb = cv2.ORB_create(nfeatures=2000)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 2:
        annotated = Image.fromarray(img_arr)
        return annotated, {
            "total_keypoints": len(keypoints) if keypoints else 0,
            "suspicious_matches": 0,
            "verdict": "Insufficient features for analysis",
        }

    # Self-matching with BFMatcher
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(descriptors, descriptors, k=2)

    # Filter: keep matches where the two matched keypoints are far apart
    # (same descriptor appearing in different locations = potential copy-move)
    suspicious = []
    for match_pair in matches:
        if len(match_pair) < 2:
            continue
        m, n = match_pair
        # Skip self-match (index matching itself)
        if m.queryIdx == m.trainIdx:
            continue
        # Ratio test
        if m.distance < 0.75 * n.distance:
            pt1 = keypoints[m.queryIdx].pt
            pt2 = keypoints[m.trainIdx].pt
            dist = np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)
            if dist > distance_threshold:
                suspicious.append((pt1, pt2, m.distance))

    # Draw matches on image
    annotated_arr = img_arr.copy()
    for pt1, pt2, _ in suspicious:
        cv2.circle(annotated_arr, (int(pt1[0]), int(pt1[1])), 4, (255, 0, 0), 2)
        cv2.circle(annotated_arr, (int(pt2[0]), int(pt2[1])), 4, (0, 0, 255), 2)
        cv2.line(annotated_arr, (int(pt1[0]), int(pt1[1])), (int(pt2[0]), int(pt2[1])), (0, 255, 0), 1)

    if len(suspicious) >= min_matches:
        verdict = f"Potential copy-move forgery detected — {len(suspicious)} suspicious region matches"
    elif len(suspicious) > 0:
        verdict = f"Minor similarities found ({len(suspicious)} matches) — likely natural repetition"
    else:
        verdict = "No copy-move forgery indicators detected"

    metadata = {
        "total_keypoints": len(keypoints),
        "suspicious_matches": len(suspicious),
        "verdict": verdict,
    }

    return Image.fromarray(annotated_arr), metadata


# ---------------------------------------------------------------------------
# 4. Noise Analysis
# ---------------------------------------------------------------------------

def analyze_noise(image: Image.Image, block_size: int = 64) -> tuple[Image.Image, dict]:
    """Analyze noise patterns for inconsistencies indicating tampering.

    Divides the image into blocks, estimates noise level per block,
    and highlights blocks with significantly different noise levels.
    Inconsistent noise across an image suggests compositing/splicing.

    Args:
        image: Input PIL image.
        block_size: Size of analysis blocks in pixels.

    Returns:
        (noise_map, metadata) — heatmap of noise levels and analysis stats.
    """
    img_arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    gray = cv2.cvtColor(img_arr.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    h, w = gray.shape

    # Estimate noise per block using Laplacian variance
    rows = max(1, h // block_size)
    cols = max(1, w // block_size)
    noise_grid = np.zeros((rows, cols), dtype=np.float32)

    for r in range(rows):
        for c in range(cols):
            y1, y2 = r * block_size, min((r + 1) * block_size, h)
            x1, x2 = c * block_size, min((c + 1) * block_size, w)
            block = gray[y1:y2, x1:x2].astype(np.uint8)
            noise_grid[r, c] = float(cv2.Laplacian(block, cv2.CV_32F).var())

    # Normalize for visualization
    grid_min = noise_grid.min()
    grid_max = noise_grid.max()
    if grid_max > grid_min:
        normalized = ((noise_grid - grid_min) / (grid_max - grid_min) * 255).astype(np.uint8)
    else:
        normalized = np.zeros_like(noise_grid, dtype=np.uint8)

    # Upscale to original image size for visualization
    noise_map = cv2.resize(normalized, (w, h), interpolation=cv2.INTER_NEAREST)
    noise_colored = cv2.applyColorMap(noise_map, cv2.COLORMAP_JET)
    noise_colored = cv2.cvtColor(noise_colored, cv2.COLOR_BGR2RGB)

    # Statistics
    mean_noise = float(np.mean(noise_grid))
    std_noise = float(np.std(noise_grid))
    cv_noise = std_noise / mean_noise if mean_noise > 0 else 0  # coefficient of variation

    # Detect inconsistent blocks (outliers)
    threshold = mean_noise + 2 * std_noise
    inconsistent_blocks = int(np.sum(noise_grid > threshold))
    total_blocks = rows * cols
    inconsistency_ratio = inconsistent_blocks / total_blocks if total_blocks > 0 else 0

    if cv_noise > 0.5 and inconsistency_ratio > 0.1:
        verdict = "Significant noise inconsistencies — possible image compositing"
    elif cv_noise > 0.3:
        verdict = "Moderate noise variation — review flagged regions"
    else:
        verdict = "Noise pattern is consistent — no splicing indicators"

    metadata = {
        "block_size": block_size,
        "grid_shape": [rows, cols],
        "mean_noise": round(mean_noise, 2),
        "std_noise": round(std_noise, 2),
        "coefficient_of_variation": round(cv_noise, 4),
        "inconsistent_blocks": inconsistent_blocks,
        "total_blocks": total_blocks,
        "inconsistency_ratio": round(inconsistency_ratio, 4),
        "verdict": verdict,
    }

    return Image.fromarray(noise_colored), metadata


# ---------------------------------------------------------------------------
# 5. Full Forensic Report
# ---------------------------------------------------------------------------

def run_full_analysis(
    image: Image.Image,
    file_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict:
    """Run all forensic analysis techniques and compile results.

    Args:
        image: Input PIL image.
        file_path: Original file path for metadata extraction.
        output_dir: Directory to save analysis artifacts (ELA map, etc).

    Returns:
        Dictionary with all analysis results and artifact paths.
    """
    logger.info("Starting forensic analysis...")
    results: dict = {}

    # ELA
    logger.info("Running Error Level Analysis...")
    ela_image, ela_meta = error_level_analysis(image)
    results["ela"] = ela_meta
    if output_dir:
        ela_path = output_dir / "ela_analysis.png"
        ela_image.save(ela_path)
        results["ela"]["image_path"] = str(ela_path)

    # Metadata
    logger.info("Extracting metadata...")
    results["metadata"] = extract_metadata(image, file_path)

    # Copy-Move Detection
    logger.info("Running copy-move detection...")
    cm_image, cm_meta = detect_copy_move(image)
    results["copy_move"] = cm_meta
    if output_dir:
        cm_path = output_dir / "copy_move_analysis.png"
        cm_image.save(cm_path)
        results["copy_move"]["image_path"] = str(cm_path)

    # Noise Analysis
    logger.info("Running noise analysis...")
    noise_image, noise_meta = analyze_noise(image)
    results["noise"] = noise_meta
    if output_dir:
        noise_path = output_dir / "noise_analysis.png"
        noise_image.save(noise_path)
        results["noise"]["image_path"] = str(noise_path)

    logger.info("Forensic analysis complete.")
    return results
