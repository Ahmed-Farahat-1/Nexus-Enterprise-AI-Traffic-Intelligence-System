"""
Plate Reader — ALPR pipeline using YOLO plate detection + EasyOCR.

Two-stage pipeline:
    Stage 1: YOLO plate detector finds plate bounding box in the vehicle crop.
    Stage 2: Crop, preprocess, and pass to EasyOCR for character recognition.

CRITICAL: This module is designed to run ONCE per unique Track_ID, at the
frame where the vehicle's bounding box area is largest (closest to camera).
Results are cached and never re-computed for the same vehicle.
"""

import cv2
import logging
import numpy as np
from typing import Optional

from core.model_registry import ModelRegistry
from utils.constants import PLATE_CONFIDENCE

logger = logging.getLogger(__name__)


def read_plate(vehicle_crop_bgr: np.ndarray) -> str:
    """
    Detect and read a license plate from a vehicle crop.

    Args:
        vehicle_crop_bgr: Cropped vehicle image in BGR format.

    Returns:
        Plate text string (e.g., "ABC 1234") or "" if not detected.
    """
    registry = ModelRegistry()

    # --- Stage 1: Plate Detection with YOLO ---
    plate_crop = _detect_plate_region(vehicle_crop_bgr, registry)

    if plate_crop is None:
        return ""

    # --- Stage 2: OCR on the plate crop ---
    plate_text = _run_ocr(plate_crop, registry)

    return plate_text


def _detect_plate_region(
    vehicle_crop: np.ndarray,
    registry: ModelRegistry,
) -> Optional[np.ndarray]:
    """
    Use YOLO plate detector to find the license plate within the vehicle crop.

    Returns the cropped plate image or None if no plate is detected.
    """
    detector = registry.get_plate_detector()

    if detector is None:
        # Plate detector unavailable — try heuristic crop
        return _heuristic_plate_crop(vehicle_crop)

    try:
        results = detector(vehicle_crop, verbose=False, conf=PLATE_CONFIDENCE)

        if results[0].boxes is None or len(results[0].boxes) == 0:
            return _heuristic_plate_crop(vehicle_crop)

        # Take the highest-confidence detection
        boxes = results[0].boxes
        confidences = boxes.conf.cpu().numpy()
        best_idx = np.argmax(confidences)
        x1, y1, x2, y2 = map(int, boxes.xyxy[best_idx].cpu().numpy())

        # Validate box dimensions
        h, w = vehicle_crop.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if (x2 - x1) < 10 or (y2 - y1) < 5:
            return _heuristic_plate_crop(vehicle_crop)

        plate_crop = vehicle_crop[y1:y2, x1:x2]
        return plate_crop

    except Exception as e:
        logger.warning(f"Plate detection failed: {e}")
        return _heuristic_plate_crop(vehicle_crop)


def _heuristic_plate_crop(vehicle_crop: np.ndarray) -> Optional[np.ndarray]:
    """
    Fallback: estimate plate location as the bottom-center of the vehicle.

    Heuristic: license plates are typically in the bottom 30% of the vehicle,
    centered horizontally within the middle 60%.
    """
    h, w = vehicle_crop.shape[:2]

    if h < 40 or w < 40:
        return None

    # Bottom 30%, center 60%
    y_start = int(h * 0.70)
    x_start = int(w * 0.20)
    x_end = int(w * 0.80)

    plate_region = vehicle_crop[y_start:h, x_start:x_end]

    if plate_region.shape[0] < 10 or plate_region.shape[1] < 20:
        return None

    return plate_region


def _run_ocr(plate_crop: np.ndarray, registry: ModelRegistry) -> str:
    """
    Run EasyOCR on a cropped plate image.

    Preprocessing steps:
        1. Resize to standard height
        2. Convert to grayscale
        3. Apply adaptive thresholding
        4. Run OCR

    Returns cleaned plate text or "".
    """
    reader = registry.get_ocr_reader()

    if reader is None:
        return ""

    try:
        # --- Preprocess plate crop for OCR ---
        processed = _preprocess_plate(plate_crop)

        # Run EasyOCR
        results = reader.readtext(
            processed,
            detail=0,          # Return text only, no bounding boxes
            paragraph=True,    # Merge nearby text
            allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789- ",
        )

        if not results:
            return ""

        # Join all detected text blocks
        raw_text = " ".join(results).strip().upper()

        # Clean up
        plate_text = _clean_plate_text(raw_text)

        if len(plate_text) < 3:
            # Too short to be a real plate
            return ""

        return plate_text

    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def _preprocess_plate(plate_crop: np.ndarray) -> np.ndarray:
    """
    Preprocess plate crop for better OCR accuracy.
    EasyOCR has its own internal binarization, so we just resize it.
    """
    target_h = 60
    h, w = plate_crop.shape[:2]
    if h == 0 or w == 0:
        return plate_crop

    scale = target_h / h
    target_w = int(w * scale)
    resized = cv2.resize(plate_crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

    return resized


def _clean_plate_text(raw_text: str) -> str:
    """
    Clean OCR output: remove noise characters, normalize spacing.
    """
    import re

    # Keep only alphanumeric, spaces, and dashes
    cleaned = re.sub(r'[^A-Z0-9 \-]', '', raw_text)

    # Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned
