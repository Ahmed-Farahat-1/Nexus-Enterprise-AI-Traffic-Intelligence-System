"""
Driver Monitoring System (DMS) — Detects seatbelt usage and phone usage
from the estimated windshield area of a vehicle crop.

Uses CLIP zero-shot classification to classify the driver area.

Limitations:
    - Accuracy depends heavily on camera angle, distance, and windshield visibility.
    - Reports "N/A" when the crop is too small or confidence is below threshold.
    - This is an experimental best-effort module, not safety-critical.
"""

import logging
import numpy as np
from typing import Tuple, Optional

from PIL import Image

from core.model_registry import ModelRegistry
from utils.constants import DMS_MIN_CROP_SIZE, DMS_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# CLIP zero-shot candidate labels
SEATBELT_LABELS = [
    "a person wearing a seatbelt while driving",
    "a person driving without a seatbelt",
]

PHONE_LABELS = [
    "a person using a mobile phone while driving",
    "a person driving normally without a phone",
]


def analyze_driver(vehicle_crop_bgr: np.ndarray) -> str:
    """
    Analyze the driver area of a vehicle crop for seatbelt and phone usage.

    Args:
        vehicle_crop_bgr: Full vehicle bounding-box crop in BGR format.

    Returns:
        Status string, e.g.:
            "Belt: ✅ | Phone: ❌"
            "Belt: ❌ | Phone: ✅"
            "N/A"
    """
    # --- Step 1: Extract windshield region (top ~40% of vehicle) ---
    windshield = _crop_windshield(vehicle_crop_bgr)

    if windshield is None:
        return "N/A"

    h, w = windshield.shape[:2]
    if h < DMS_MIN_CROP_SIZE or w < DMS_MIN_CROP_SIZE:
        return "N/A"

    registry = ModelRegistry()
    processor, model = registry.get_clip()

    if processor is None or model is None:
        return "N/A"

    try:
        # Convert BGR → RGB → PIL
        rgb = windshield[:, :, ::-1]
        pil_image = Image.fromarray(rgb)

        import torch

        # --- Step 2: Classify seatbelt ---
        seatbelt_status = _clip_classify(
            pil_image, SEATBELT_LABELS, processor, model
        )

        # --- Step 3: Classify phone usage ---
        phone_status = _clip_classify(
            pil_image, PHONE_LABELS, processor, model
        )

        # Build result string
        belt_str = _format_seatbelt(seatbelt_status)
        phone_str = _format_phone(phone_status)

        return f"{belt_str} | {phone_str}"

    except Exception as e:
        logger.warning(f"DMS analysis failed: {e}")
        return "N/A"


def _crop_windshield(vehicle_crop: np.ndarray) -> Optional[np.ndarray]:
    """
    Estimate the windshield area as the top portion of the vehicle crop.

    The windshield is typically in the top 40% of the bounding box for
    front-facing vehicles, or top 35% for rear-facing.
    We take a generous top 40% with some horizontal margin.
    """
    h, w = vehicle_crop.shape[:2]

    if h < 30 or w < 30:
        return None

    # Top 40% of height, center 80% of width
    y_end = int(h * 0.40)
    x_start = int(w * 0.10)
    x_end = int(w * 0.90)

    windshield = vehicle_crop[0:y_end, x_start:x_end]

    if windshield.shape[0] < 15 or windshield.shape[1] < 15:
        return None

    return windshield


def _clip_classify(
    image: Image.Image,
    candidate_labels: list,
    processor,
    model,
) -> Tuple[int, float]:
    """
    Run CLIP zero-shot classification on an image.

    Args:
        image: PIL image to classify.
        candidate_labels: List of text descriptions.
        processor: CLIP processor.
        model: CLIP model.

    Returns:
        (best_label_index, confidence)
    """
    import torch

    inputs = processor(
        text=candidate_labels,
        images=image,
        return_tensors="pt",
        padding=True,
    )

    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    # Compute softmax probabilities
    logits = outputs.logits_per_image  # (1, num_labels)
    probs = logits.softmax(dim=1).cpu().numpy()[0]

    best_idx = int(np.argmax(probs))
    confidence = float(probs[best_idx])

    return best_idx, confidence


def _format_seatbelt(result: Tuple[int, float]) -> str:
    """Format seatbelt classification result."""
    idx, conf = result

    if conf < DMS_CONFIDENCE_THRESHOLD:
        return "Belt: ?"

    # Index 0 = wearing seatbelt, Index 1 = not wearing
    if idx == 0:
        return "Belt: ✅"
    else:
        return "Belt: ❌"


def _format_phone(result: Tuple[int, float]) -> str:
    """Format phone usage classification result."""
    idx, conf = result

    if conf < DMS_CONFIDENCE_THRESHOLD:
        return "Phone: ?"

    # Index 0 = using phone, Index 1 = not using phone
    if idx == 0:
        return "Phone: ✅"
    else:
        return "Phone: ❌"
