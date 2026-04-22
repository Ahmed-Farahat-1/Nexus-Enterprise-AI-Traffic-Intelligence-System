"""
Vehicle Descriptor — Extracts vehicle type and color using BLIP captioning.

Receives a cropped vehicle image, runs it through BLIP-image-captioning-base,
and parses the output to extract structured (color, type) information.

This runs as a slave model — called asynchronously, once per Track_ID.
"""

import logging
import re
from typing import Optional, Tuple

import numpy as np
from PIL import Image

from core.model_registry import ModelRegistry
from utils.constants import BLIP_MAX_TOKENS

logger = logging.getLogger(__name__)

# --- Known vehicle types and colors for structured parsing ---
KNOWN_COLORS = [
    "red", "blue", "green", "black", "white", "silver", "gray", "grey",
    "yellow", "orange", "brown", "gold", "beige", "maroon", "navy",
    "purple", "burgundy", "tan", "cream", "dark", "light",
]

KNOWN_TYPES = [
    "sedan", "suv", "truck", "pickup", "van", "minivan", "hatchback",
    "coupe", "convertible", "wagon", "bus", "motorcycle", "motorbike",
    "car", "vehicle", "jeep", "crossover", "limousine",
]


def describe_vehicle(crop_bgr: np.ndarray) -> str:
    """
    Generate a vehicle description (type + color) from a BGR crop.

    Args:
        crop_bgr: Vehicle bounding-box crop in BGR format (OpenCV).

    Returns:
        Description string like "Silver SUV" or "Red Sedan".
        Returns "Vehicle" if BLIP is unavailable or parsing fails.
    """
    registry = ModelRegistry()
    processor, model = registry.get_blip()

    if processor is None or model is None:
        # BLIP not available — fallback to simple description
        return _fallback_color_detection(crop_bgr)

    try:
        # Convert BGR → RGB → PIL
        rgb = crop_bgr[:, :, ::-1]
        pil_image = Image.fromarray(rgb)

        # --- CHANGED: Use constrained captioning with a vehicle-specific prompt ---
        prompt = "this is a photo of a"
        inputs = processor(pil_image, text=prompt, return_tensors="pt")

        # Move to same device as model
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        import torch
        with torch.no_grad():
            output_ids = model.generate(
                **inputs,
                max_new_tokens=BLIP_MAX_TOKENS,
                num_beams=3,
            )

        caption = processor.decode(output_ids[0], skip_special_tokens=True)
        caption = caption.lower().strip()

        # Parse color and type from caption
        color, vtype = _parse_description(caption)

        if color and vtype:
            return f"{color.title()} {vtype.title()}"
        elif color:
            return f"{color.title()} Vehicle"
        elif vtype:
            return vtype.title()
        else:
            return "Vehicle"

    except Exception as e:
        logger.warning(f"BLIP inference failed: {e}")
        return _fallback_color_detection(crop_bgr)


def _parse_description(caption: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract color and vehicle type from a BLIP caption string.

    Example: "this is a photo of a silver suv parked on the road"
    → ("silver", "suv")
    """
    color = None
    vtype = None

    words = caption.split()

    for word in words:
        clean = re.sub(r'[^a-zA-Z]', '', word)
        if clean in KNOWN_COLORS and color is None:
            color = clean
        if clean in KNOWN_TYPES and vtype is None:
            vtype = clean

    return color, vtype


def _fallback_color_detection(crop_bgr: np.ndarray) -> str:
    """
    Simple HSV-based dominant color detection as a fallback
    when BLIP is unavailable.
    """
    try:
        import cv2

        # Resize for speed
        small = cv2.resize(crop_bgr, (64, 64))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)

        # Get average hue and saturation
        avg_h = np.mean(hsv[:, :, 0])
        avg_s = np.mean(hsv[:, :, 1])
        avg_v = np.mean(hsv[:, :, 2])

        # Simple color classification
        if avg_s < 40:
            if avg_v < 60:
                return "Black Vehicle"
            elif avg_v > 200:
                return "White Vehicle"
            else:
                return "Silver Vehicle"
        elif avg_h < 10 or avg_h > 170:
            return "Red Vehicle"
        elif 10 <= avg_h < 25:
            return "Orange Vehicle"
        elif 25 <= avg_h < 35:
            return "Yellow Vehicle"
        elif 35 <= avg_h < 85:
            return "Green Vehicle"
        elif 85 <= avg_h < 130:
            return "Blue Vehicle"
        else:
            return "Vehicle"
    except Exception:
        return "Vehicle"
