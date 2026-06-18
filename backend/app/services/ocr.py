from __future__ import annotations

from dataclasses import dataclass
from PIL import Image


@dataclass
class OCRResult:
    text: str
    confidence: float | None
    normalized_edit_distance: float | None
    available: bool
    note: str | None = None


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            insert = curr[j - 1] + 1
            delete = prev[j] + 1
            replace = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(insert, delete, replace))
        prev = curr
    return prev[-1]


def run_ocr(image_path: str, reference_text: str | None = None) -> OCRResult:
    try:
        import pytesseract
    except Exception:
        return OCRResult("", None, None, False, "pytesseract not installed")

    image = Image.open(image_path).convert("RGB")
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return OCRResult("", None, None, False, f"Tesseract OCR unavailable: {exc}")
    words: list[str] = []
    confs: list[float] = []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        txt = (txt or "").strip()
        if not txt:
            continue
        words.append(txt)
        try:
            conf_val = float(conf)
            if conf_val >= 0:
                confs.append(conf_val)
        except ValueError:
            continue
    text = " ".join(words)
    avg_conf = sum(confs) / len(confs) if confs else None

    norm_dist = None
    if reference_text:
        ref = reference_text.strip().lower()
        pred = text.strip().lower()
        if ref:
            norm_dist = _levenshtein(ref, pred) / max(len(ref), 1)

    return OCRResult(text, avg_conf, norm_dist, True, None)
