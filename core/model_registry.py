"""
Model Registry — Centralized lazy-loading and lifecycle management
for all AI models in the multi-model pipeline.

Models are loaded on first access and cached as singletons.
Thread-safe access is ensured via threading locks.

Model inventory:
    1. YOLOv8 Tracker (master) — already loaded by TrafficAnalyzer
    2. BLIP Image Captioner — vehicle type & color description
    3. YOLO Plate Detector — license plate bounding box detection
    4. EasyOCR Reader — OCR on cropped plate images
    5. CLIP Zero-Shot — driver monitoring (seatbelt, phone)
"""

import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Singleton registry for all AI models.

    All heavy models are loaded lazily on first call to their getter.
    This prevents a 30+ second cold start when the application launches.
    Failed model loads are caught and logged — the feature is disabled
    gracefully rather than crashing the application.
    """

    _instance: Optional["ModelRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Model slots
        self._blip_processor = None
        self._blip_model = None
        self._blip_lock = threading.Lock()
        self._blip_available = True

        self._plate_detector = None
        self._plate_lock = threading.Lock()
        self._plate_available = True

        self._ocr_reader = None
        self._ocr_lock = threading.Lock()
        self._ocr_available = True

        self._clip_processor = None
        self._clip_model = None
        self._clip_lock = threading.Lock()
        self._clip_available = True

        # Device detection
        self._device = self._detect_device()
        logger.info(f"ModelRegistry initialized — device: {self._device}")

    @staticmethod
    def _detect_device() -> str:
        """Detect whether CUDA GPU is available."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    @property
    def device(self) -> str:
        return self._device

    # -------------------------------------------------
    # BLIP — Vehicle Description
    # -------------------------------------------------

    def get_blip(self):
        """
        Returns (processor, model) for BLIP image captioning.
        Loads on first call. Returns (None, None) if unavailable.
        """
        if not self._blip_available:
            return None, None

        if self._blip_model is None:
            with self._blip_lock:
                if self._blip_model is None:
                    try:
                        from transformers import BlipProcessor, BlipForConditionalGeneration
                        from utils.constants import BLIP_MODEL_NAME

                        logger.info(f"Loading BLIP model: {BLIP_MODEL_NAME}...")
                        self._blip_processor = BlipProcessor.from_pretrained(BLIP_MODEL_NAME)
                        self._blip_model = BlipForConditionalGeneration.from_pretrained(
                            BLIP_MODEL_NAME
                        )
                        if self._device == "cuda":
                            self._blip_model = self._blip_model.to("cuda")
                        self._blip_model.eval()
                        logger.info("BLIP model loaded successfully.")
                    except Exception as e:
                        logger.error(f"Failed to load BLIP model: {e}")
                        self._blip_available = False
                        return None, None

        return self._blip_processor, self._blip_model

    @property
    def blip_available(self) -> bool:
        return self._blip_available

    # -------------------------------------------------
    # Plate Detector — YOLOv8 fine-tuned for plates
    # -------------------------------------------------

    def get_plate_detector(self):
        """
        Returns a YOLO model for license plate detection.
        Disabled (returns None) due to HF auth issues, triggering heuristic fallback.
        """
        if not self._plate_available:
            return None

        # DISABLED to prevent HuggingFace 401 Unauthorized crashes during download.
        # Fallback to _heuristic_plate_crop in plate_reader.py
        self._plate_available = False
        return None

    @property
    def plate_available(self) -> bool:
        return self._plate_available

    # -------------------------------------------------
    # EasyOCR — Optical Character Recognition
    # -------------------------------------------------

    def get_ocr_reader(self):
        """
        Returns an EasyOCR Reader instance.
        Loads on first call. Returns None if unavailable.
        """
        if not self._ocr_available:
            return None

        if self._ocr_reader is None:
            with self._ocr_lock:
                if self._ocr_reader is None:
                    try:
                        import easyocr
                        from utils.constants import OCR_LANGUAGES

                        logger.info("Loading EasyOCR reader...")
                        gpu = self._device == "cuda"
                        self._ocr_reader = easyocr.Reader(
                            OCR_LANGUAGES, gpu=gpu, verbose=False
                        )
                        logger.info("EasyOCR reader loaded successfully.")
                    except Exception as e:
                        logger.error(f"Failed to load EasyOCR: {e}")
                        self._ocr_available = False
                        return None

        return self._ocr_reader

    @property
    def ocr_available(self) -> bool:
        return self._ocr_available

    # -------------------------------------------------
    # CLIP — Zero-Shot Classification (DMS)
    # -------------------------------------------------

    def get_clip(self):
        """
        Returns (processor, model) for CLIP zero-shot classification.
        Loads on first call. Returns (None, None) if unavailable.
        """
        if not self._clip_available:
            return None, None

        if self._clip_model is None:
            with self._clip_lock:
                if self._clip_model is None:
                    try:
                        from transformers import CLIPProcessor, CLIPModel
                        from utils.constants import CLIP_MODEL_NAME

                        logger.info(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
                        self._clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
                        self._clip_model = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
                        if self._device == "cuda":
                            self._clip_model = self._clip_model.to("cuda")
                        self._clip_model.eval()
                        logger.info("CLIP model loaded successfully.")
                    except Exception as e:
                        logger.error(f"Failed to load CLIP model: {e}")
                        self._clip_available = False
                        return None, None

        return self._clip_processor, self._clip_model

    @property
    def clip_available(self) -> bool:
        return self._clip_available

    # -------------------------------------------------
    # Lifecycle
    # -------------------------------------------------

    def unload_all(self):
        """Release all models from memory."""
        import gc

        self._blip_processor = None
        self._blip_model = None
        self._plate_detector = None
        self._ocr_reader = None
        self._clip_processor = None
        self._clip_model = None

        gc.collect()

        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

        logger.info("All models unloaded.")

    def status_report(self) -> dict:
        """Get a summary of which models are loaded and available."""
        return {
            "device": self._device,
            "blip": {
                "available": self._blip_available,
                "loaded": self._blip_model is not None,
            },
            "plate_detector": {
                "available": self._plate_available,
                "loaded": self._plate_detector is not None,
            },
            "ocr": {
                "available": self._ocr_available,
                "loaded": self._ocr_reader is not None,
            },
            "clip": {
                "available": self._clip_available,
                "loaded": self._clip_model is not None,
            },
        }
