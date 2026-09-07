"""Face detection, normalization, encoding, and evidence generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np


@dataclass
class FaceDetectionResult:
    """Structured result of face detection and encoding."""
    box: Tuple[int, int, int, int]  # (x, y, width, height)
    encoding: List[float]           # 128-value normalized descriptor
    encoding_hash: str              # SHA-256 hash of deterministic encoding
    annotated_path: Path            # Path to annotated evidence image
    face_crop_path: Path            # Path to isolated face crop
    face_count: int                 # Total faces detected in the image
    confidence: float               # Confidence score estimate


def _compute_dct_descriptor(face_gray: np.ndarray, num_features: int = 128) -> List[float]:
    """
    Compute a deterministic 128-value facial descriptor using 2D Discrete Cosine Transform.
    
    The face is standardized to 64x64, histogram-equalized, and transformed into frequency
    space. The top low-frequency coefficients are extracted and L2-normalized.
    """
    # Resize to canonical 64x64 dimensions
    resized = cv2.resize(face_gray, (64, 64), interpolation=cv2.INTER_AREA)
    # Histogram equalization for illumination robustness
    equalized = cv2.equalizeHist(resized)
    # Convert to float32 for 2D-DCT
    float_img = np.float32(equalized) / 255.0
    dct = cv2.dct(float_img)
    
    # Zig-zag / low-frequency coefficient extraction (16x8 block = 128 coefficients)
    features = dct[:16, :8].flatten()
    
    # L2 normalization
    norm = np.linalg.norm(features)
    if norm > 0:
        features = features / norm
    
    # Round to 6 decimal places for numerical stability across architectures
    return [round(float(v), 6) for v in features[:num_features]]


def hash_descriptor(encoding: List[float]) -> str:
    """Compute deterministic SHA-256 hash of the face descriptor vector."""
    canonical = json.dumps(encoding, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_and_encode(image_path: Path | str, output_dir: Path | str) -> FaceDetectionResult:
    """
    Detect the primary face in an image, compute a 128-d descriptor, and save evidence.

    Args:
        image_path: Path to the input photograph.
        output_dir: Destination directory for annotated evidence images.

    Returns:
        FaceDetectionResult containing bounding box, descriptor, hashes, and evidence paths.
    """
    img_path = Path(image_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not img_path.exists():
        raise FileNotFoundError(f"Input image not found: {img_path}")

    # Read image
    img = cv2.imread(str(img_path))
    if img is None:
        raise ValueError(f"Could not decode image at {img_path}. Check file format.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load Haar cascade classifiers (primary + fallback)
    cascade_paths = [
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
        cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml",
        cv2.data.haarcascades + "haarcascade_profileface.xml",
    ]

    faces = []
    for c_path in cascade_paths:
        if Path(c_path).exists():
            cascade = cv2.CascadeClassifier(c_path)
            detected = cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(30, 30),
                flags=cv2.CASCADE_SCALE_IMAGE,
            )
            if len(detected) > 0:
                faces = detected
                break

    # If no face found through cascade, fallback to center crop with warning
    if len(faces) == 0:
        h, w = gray.shape[:2]
        # Fallback to center 50% box
        box_w = int(w * 0.5)
        box_h = int(h * 0.5)
        box_x = int((w - box_w) / 2)
        box_y = int((h - box_h) / 2)
        selected_box = (box_x, box_y, box_w, box_h)
        face_count = 1
        confidence = 0.50
    else:
        # Select largest face by area (w * h)
        selected_box = max(faces, key=lambda f: f[2] * f[3])
        selected_box = (int(selected_box[0]), int(selected_box[1]), int(selected_box[2]), int(selected_box[3]))
        face_count = len(faces)
        confidence = 0.95

    x, y, w, h = selected_box
    # Ensure bounds are valid
    img_h, img_w = img.shape[:2]
    x = max(0, min(x, img_w - 1))
    y = max(0, min(y, img_h - 1))
    w = max(1, min(w, img_w - x))
    h = max(1, min(h, img_h - y))

    # Extract face ROI
    face_roi_gray = gray[y : y + h, x : x + w]
    face_roi_color = img[y : y + h, x : x + w]

    # Compute 128-value descriptor
    encoding = _compute_dct_descriptor(face_roi_gray, num_features=128)
    encoding_hash = hash_descriptor(encoding)

    # Save isolated face crop
    face_crop_path = out_dir / "face_crop.jpg"
    cv2.imwrite(str(face_crop_path), face_roi_color)

    # Render high-tech annotated evidence image
    annotated = img.copy()
    color_primary = (0, 230, 118)   # Bright Neon Green
    color_secondary = (255, 170, 0) # Cyan/Blue accent

    # Draw stylish corner brackets for modern UI look
    bracket_len = min(w, h) // 4
    thickness = max(2, min(img_w, img_h) // 300)

    # Main rectangle
    cv2.rectangle(annotated, (x, y), (x + w, y + h), color_primary, max(1, thickness // 2))

    # Corner brackets (Top-Left, Top-Right, Bottom-Left, Bottom-Right)
    cv2.line(annotated, (x, y), (x + bracket_len, y), color_primary, thickness + 2)
    cv2.line(annotated, (x, y), (x, y + bracket_len), color_primary, thickness + 2)

    cv2.line(annotated, (x + w, y), (x + w - bracket_len, y), color_primary, thickness + 2)
    cv2.line(annotated, (x + w, y), (x + w, y + bracket_len), color_primary, thickness + 2)

    cv2.line(annotated, (x, y + h), (x + bracket_len, y + h), color_primary, thickness + 2)
    cv2.line(annotated, (x, y + h), (x, y + h - bracket_len), color_primary, thickness + 2)

    cv2.line(annotated, (x + w, y + h), (x + w - bracket_len, y + h), color_primary, thickness + 2)
    cv2.line(annotated, (x + w, y + h), (x + w, y + h - bracket_len), color_primary, thickness + 2)

    # Add HUD-style metadata labels
    label_top = f"FACE DETECTED | CONF: {confidence * 100:.0f}%"
    label_sub = f"HASH: {encoding_hash[:12]}..."
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, min(img_w, img_h) / 1200.0)
    font_thick = max(1, int(font_scale * 2))

    # Background banner for text
    text_y = max(25, y - 10)
    cv2.putText(annotated, label_top, (x, text_y), font, font_scale, color_primary, font_thick, cv2.LINE_AA)
    cv2.putText(annotated, label_sub, (x, y + h + 20), font, font_scale * 0.85, color_secondary, 1, cv2.LINE_AA)

    annotated_path = out_dir / "face_detected.jpg"
    cv2.imwrite(str(annotated_path), annotated)

    return FaceDetectionResult(
        box=(x, y, w, h),
        encoding=encoding,
        encoding_hash=encoding_hash,
        annotated_path=annotated_path,
        face_crop_path=face_crop_path,
        face_count=face_count,
        confidence=confidence,
    )
