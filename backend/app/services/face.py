from __future__ import annotations

import cv2
import numpy as np


def _detect_largest_face(image_bgr: np.ndarray) -> np.ndarray | None:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    classifier = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = classifier.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return None
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    return image_bgr[y : y + h, x : x + w]


def _embedding(face_bgr: np.ndarray) -> np.ndarray:
    resized = cv2.resize(face_bgr, (112, 112), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [128], [0, 256]).reshape(-1).astype(np.float32)
    hist /= max(np.linalg.norm(hist), 1e-6)
    return hist


def face_similarity(image_path: str, reference_image_path: str | None = None) -> dict:
    if not reference_image_path:
        return {"available": False, "score": None, "note": "No reference face image provided"}

    img = cv2.imread(image_path)
    ref = cv2.imread(reference_image_path)
    if img is None or ref is None:
        return {"available": False, "score": None, "note": "Failed to read image/reference"}

    face = _detect_largest_face(img)
    face_ref = _detect_largest_face(ref)
    if face is None or face_ref is None:
        return {"available": False, "score": None, "note": "No face detected in one or both images"}

    emb_a = _embedding(face)
    emb_b = _embedding(face_ref)
    score = float(np.dot(emb_a, emb_b))
    return {
        "available": True,
        "score": score,
        "note": "Histogram-based proxy score (higher is closer).",
    }

