"""
Traffic Analyzer — Core AI processing logic (v2.0 — Multi-Model Pipeline).

Major changes from v1.0:
    1. REPLACED: K/bbox_height speed estimation → Bird's-Eye View (BEV)
       homography-based calibrated speed computation.
    2. ADDED: Slave model orchestration for vehicle description, plate
       reading, and driver monitoring.
    3. EXPANDED: FrameResult now includes per-vehicle VehicleInfo with
       type, color, plate number, and driver status.
    4. MAINTAINED: Wrong-way detection logic (unchanged).

Architecture:
    Master: YOLOv8 + ByteTrack (runs every frame)
    Slaves: BLIP, YOLO-Plate+EasyOCR, CLIP-DMS (run once per Track_ID)
"""

import cv2
import time
import logging
import numpy as np
from dataclasses import dataclass, field
from collections import defaultdict
from typing import List, Optional, Dict
from ultralytics import YOLO

from core.calibration import BirdEyeViewCalibrator, SpeedSmoother
from utils.constants import (
    YOLO_MODEL, YOLO_CONFIDENCE, VEHICLE_CLASSES, COCO_CLASS_NAMES,
    HISTORY_LENGTH, SPEED_FRAME_DIFF, DIRECTION_FRAME_DIFF,
    DIRECTION_THRESHOLD, DENSITY_JAM_VEHICLES, DENSITY_JAM_SPEED,
    DENSITY_HIGH_VEHICLES, DENSITY_MEDIUM_VEHICLES,
    SUDDEN_STOP_HIGH_SPEED, SUDDEN_STOP_LOW_SPEED,
    SLOW_SPEED_THRESHOLD, STOPPED_SPEED_THRESHOLD,
    SPEED_MAX_PLAUSIBLE,
    CV_COLOR_NORMAL, CV_COLOR_WRONG_WAY, CV_COLOR_SUDDEN_STOP,
    CV_COLOR_TEXT, CV_COLOR_LANE_LINE, CV_COLOR_PLATE,
    DIRECTION_MODE_STANDARD, DIRECTION_RULES,
    PLATE_READ_PATIENCE_FRAMES,
)

logger = logging.getLogger(__name__)


# ==========================================
# 📦 DATA CLASSES
# ==========================================

@dataclass
class VehicleEvent:
    """Represents a detected traffic event."""
    vehicle_id: int
    event_type: str      # "WRONG WAY" or "SUDDEN STOP"
    timestamp: str       # HH:MM:SS
    lane: str            # "LEFT" or "RIGHT"
    vehicle_desc: str = ""
    plate_number: str = ""


@dataclass
class VehicleInfo:
    """
    Rich per-vehicle data for the dashboard table.
    --- NEW in v2.0 ---
    """
    track_id: int
    speed_kmh: float
    direction: str        # "UP" / "DOWN" / "UNKNOWN"
    lane: str             # "LEFT" / "RIGHT"
    behavior: str         # "NORMAL" / "WRONG WAY" / "SUDDEN STOP" / etc.
    vehicle_desc: str     # "Silver SUV" or "⏳" while pending
    plate_number: str     # "ABC 1234" or "—"
    driver_status: str    # "Belt: ✅ | Phone: ❌" or "N/A"
    coco_class: int = 2   # COCO class ID for fallback


@dataclass
class FrameResult:
    """Contains all data from processing a single frame."""
    annotated_frame: np.ndarray
    vehicle_count: int = 0
    average_speed: float = 0.0
    density_status: str = "LOW"
    events: List[VehicleEvent] = field(default_factory=list)
    vehicles: List[VehicleInfo] = field(default_factory=list)  # NEW in v2.0
    fps: float = 0.0
    frame_number: int = 0


# ==========================================
# 🧠 TRAFFIC ANALYZER (v2.0)
# ==========================================

class TrafficAnalyzer:
    """
    Core traffic analysis engine with multi-model pipeline support.

    v2.0 Changes:
        - BEV-calibrated speed estimation (replaces K/bbox_height)
        - Slave model result caching and orchestration
        - Expanded per-vehicle metadata
    """

    def __init__(self):
        self.model: Optional[YOLO] = None
        self._model_loaded = False

        # --- BEV Calibrator (CHANGED: replaces K constant) ---
        self.calibrator = BirdEyeViewCalibrator()
        self._calibrator_initialized = False

        # Per-vehicle tracking history
        self.track_history: Dict[int, dict] = defaultdict(lambda: {
            "centers_x": [],
            "centers_y": [],
            "heights": [],
            "speeds": [],
            "last_seen_frame": 0,
            "speed_smoother": SpeedSmoother(),
        })

        # --- Slave model result caches (NEW in v2.0) ---
        # These are populated asynchronously by the VideoThread's thread pool.
        self.description_cache: Dict[int, str] = {}     # Track_ID → "Silver SUV"
        self.plate_cache: Dict[int, str] = {}            # Final confirmed ALPR
        self.plate_history: Dict[int, list] = defaultdict(list)  # ALPR voting buffer
        self.plate_locked: set = set()                   # IDs with confirmed plate
        self.dms_cache: Dict[int, str] = {}              # Track_ID → "Belt: ✅ | Phone: ❌"

        # Track which IDs have been dispatched for slave processing
        self.description_dispatched: set = set()
        self.plate_dispatched: set = set()
        self.dms_dispatched: set = set()

        # Best bbox area tracking for plate timing optimization
        self.best_bbox_area: Dict[int, float] = {}
        self.best_bbox_crop: Dict[int, np.ndarray] = {}

        # Coordinate EMA smoothing for flicker-free OSD
        self.bbox_ema: Dict[int, tuple] = {}

        # Interactive UI states
        self.divider_x_ratio = 0.5

        # Feature toggles
        self.speed_enabled = True
        self.wrong_way_enabled = True
        self.density_enabled = True

        # Traffic direction mode
        self.direction_mode = DIRECTION_MODE_STANDARD

        # FPS calculation
        self._fps_start_time = time.time()
        self._fps_frame_count = 0
        self._current_fps = 0.0

    def load_model(self):
        """Load the YOLO model. Call once before processing."""
        if not self._model_loaded:
            self.model = YOLO(YOLO_MODEL)
            self._model_loaded = True

    def reset(self):
        """Clear all tracking state for a new video source."""
        self.track_history.clear()
        self.description_cache.clear()
        self.plate_cache.clear()
        self.plate_history.clear()
        self.plate_locked.clear()
        self.dms_cache.clear()
        self.description_dispatched.clear()
        self.plate_dispatched.clear()
        self.dms_dispatched.clear()
        self.best_bbox_area.clear()
        self.best_bbox_crop.clear()
        self.bbox_ema.clear()

        self._calibrator_initialized = False
        self.calibrator = BirdEyeViewCalibrator()

        self._fps_start_time = time.time()
        self._fps_frame_count = 0
        self._current_fps = 0.0

    # ==========================================
    # 🧠 DETECTION FUNCTIONS
    # ==========================================

    def get_lane(self, x_center: float, frame_width: int) -> str:
        """Classify vehicle lane based on adjustable horizontal divider."""
        return "LEFT" if x_center < (frame_width * self.divider_x_ratio) else "RIGHT"

    @staticmethod
    def detect_direction(centers_y: list) -> str:
        """Determine movement direction from Y-coordinate history."""
        if len(centers_y) < DIRECTION_FRAME_DIFF:
            return "STATIONARY"
        dy = centers_y[-1] - centers_y[-DIRECTION_FRAME_DIFF]
        if dy > DIRECTION_THRESHOLD:
            return "DOWN"
        elif dy < -DIRECTION_THRESHOLD:
            return "UP"
        return "STATIONARY"

    def check_wrong_way(self, lane: str, direction: str) -> bool:
        """
        Flag wrong-way driving based on the active direction mode.
        """
        rules = DIRECTION_RULES.get(
            self.direction_mode, DIRECTION_RULES[DIRECTION_MODE_STANDARD]
        )
        expected_direction = rules.get(lane)
        if direction != expected_direction and direction != "STATIONARY":
            return True
        return False

    @staticmethod
    def check_sudden_stop(current_speed: float, speed_history: list) -> bool:
        """Detect if vehicle dropped rapidly from high speed to near-zero."""
        if not speed_history:
            return False
        max_recent_speed = max(speed_history)
        return max_recent_speed > SUDDEN_STOP_HIGH_SPEED and current_speed < SUDDEN_STOP_LOW_SPEED

    @staticmethod
    def get_traffic_density(vehicle_count: int, avg_speed: float) -> str:
        """Classify overall traffic density."""
        if vehicle_count > DENSITY_JAM_VEHICLES and avg_speed < DENSITY_JAM_SPEED:
            return "TRAFFIC JAM"
        elif vehicle_count > DENSITY_HIGH_VEHICLES:
            return "HIGH"
        elif vehicle_count > DENSITY_MEDIUM_VEHICLES:
            return "MEDIUM"
        else:
            return "LOW"

    # ==========================================
    # 🏎️ BEV SPEED ESTIMATION (NEW — replaces K/bbox_height)
    # ==========================================

    def compute_speed_bev(
        self,
        hist: dict,
        x_center: float,
        y_center: float,
        fps: float,
    ) -> float:
        """
        Compute calibrated speed using Bird's-Eye View transformation.

        CHANGED from v1.0: Instead of K/bbox_height, we project the
        vehicle's center point into the BEV metric space and compute
        the Euclidean distance traveled over time.

        Args:
            hist: Per-vehicle tracking history dict.
            x_center: Current x-center in pixels.
            y_center: Current y-center in pixels.
            fps: Video FPS for time calculation.

        Returns:
            Speed in km/h, smoothed via EMA.
        """
        if not self.calibrator.is_calibrated:
            return 0.0

        if len(hist["centers_x"]) < SPEED_FRAME_DIFF:
            return 0.0

        # Previous position (SPEED_FRAME_DIFF frames ago)
        prev_x = hist["centers_x"][-SPEED_FRAME_DIFF]
        prev_y = hist["centers_y"][-SPEED_FRAME_DIFF]

        # Time delta
        dt = SPEED_FRAME_DIFF / fps

        # Compute calibrated speed via homography projection
        raw_speed = self.calibrator.compute_speed(
            prev_pos_px=(prev_x, prev_y),
            curr_pos_px=(x_center, y_center),
            dt_seconds=dt,
        )

        # Smooth with EMA to reduce jitter
        smoother: SpeedSmoother = hist["speed_smoother"]
        smoothed = smoother.update(raw_speed)

        return min(smoothed, SPEED_MAX_PLAUSIBLE)

    # ==========================================
    # 🖐️ FRAME ANNOTATION
    # ==========================================

    def _draw_lane_overlay(self, frame: np.ndarray, width: int, height: int):
        """Draw lane divider and direction labels based on active mode and dynamic slider."""
        rules = DIRECTION_RULES.get(
            self.direction_mode, DIRECTION_RULES[DIRECTION_MODE_STANDARD]
        )
        left_dir = rules["LEFT"]
        right_dir = rules["RIGHT"]

        divider_x = int(width * self.divider_x_ratio)
        left_center_x = divider_x // 2
        right_center_x = divider_x + (width - divider_x) // 2

        # Draw semi-transparent line
        overlay = frame.copy()
        cv2.line(overlay, (divider_x, 0), (divider_x, height), CV_COLOR_LANE_LINE, 2)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        # Draw Labels
        cv2.putText(frame, f"{left_dir}", (left_center_x - 30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, CV_COLOR_LANE_LINE, 2, cv2.LINE_AA)
        cv2.putText(frame, f"{right_dir}", (right_center_x - 30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, CV_COLOR_LANE_LINE, 2, cv2.LINE_AA)

        if left_dir == "DOWN":
            cv2.arrowedLine(frame, (left_center_x, 65), (left_center_x, 110),
                            CV_COLOR_LANE_LINE, 2, tipLength=0.4)
        else:
            cv2.arrowedLine(frame, (left_center_x, 110), (left_center_x, 65),
                            CV_COLOR_LANE_LINE, 2, tipLength=0.4)

        if right_dir == "DOWN":
            cv2.arrowedLine(frame, (right_center_x, 65), (right_center_x, 110),
                            CV_COLOR_LANE_LINE, 2, tipLength=0.4)
        else:
            cv2.arrowedLine(frame, (right_center_x, 110), (right_center_x, 65),
                            CV_COLOR_LANE_LINE, 2, tipLength=0.4)

    def _draw_vehicle_box(
        self, frame, x1, y1, x2, y2, track_id,
        lane, speed, behavior, color,
        vehicle_desc: str = "", plate: str = "", driver_status: str = "",
    ):
        """
        Draw bounding box with professional translucent overlays,
        flicker-free EMA coordinate smoothing, and anti-aliased grouped text.
        """
        # --- EMA Smoothing for BBox Coordinates ---
        w_curr, h_curr = (x2 - x1), (y2 - y1)
        cx_curr, cy_curr = x1 + w_curr / 2.0, y1 + h_curr / 2.0

        if track_id not in self.bbox_ema:
            self.bbox_ema[track_id] = (cx_curr, cy_curr, w_curr, h_curr)
        else:
            # Alpha for smoothing (lower = smoother but lags, higher = responsive)
            alpha = 0.4
            cx_ema, cy_ema, w_ema, h_ema = self.bbox_ema[track_id]
            cx_ema = alpha * cx_curr + (1 - alpha) * cx_ema
            cy_ema = alpha * cy_curr + (1 - alpha) * cy_ema
            w_ema  = alpha * w_curr + (1 - alpha) * w_ema
            h_ema  = alpha * h_curr + (1 - alpha) * h_ema
            self.bbox_ema[track_id] = (cx_ema, cy_ema, w_ema, h_ema)

        cx, cy, w, h = self.bbox_ema[track_id]
        sx1, sy1 = int(cx - w / 2), int(cy - h / 2)
        sx2, sy2 = int(cx + w / 2), int(cy + h / 2)

        # Clamp to frame
        fh, fw = frame.shape[:2]
        sx1, sy1 = max(0, sx1), max(0, sy1)
        sx2, sy2 = min(fw, sx2), min(fh, sy2)

        # Draw main box (clean bracket style corners instead of full box if possible, 
        # but a crisp thin box is standard)
        cv2.rectangle(frame, (sx1, sy1), (sx2, sy2), color, 1, cv2.LINE_AA)

        # --- Group Information ---
        # Top Header: ID and Behavior
        header_text = f"ID:{track_id} | {speed} km/h | {behavior}"
        
        # Subtitle: Plate | Desc | Status
        sub_parts = []
        if plate: sub_parts.append(f"[{plate}]")
        if vehicle_desc: sub_parts.append(vehicle_desc)
        if driver_status and driver_status != "N/A": 
            sub_parts.append(driver_status.replace("Belt:", "B:").replace("Phone:", "P:"))
        sub_text = " | ".join(sub_parts)
        
        # Calculate background panel size
        header_font_scale, sub_font_scale = 0.5, 0.4
        thickness = 1
        font = cv2.FONT_HERSHEY_SIMPLEX

        (h_w, h_h), _ = cv2.getTextSize(header_text, font, header_font_scale, thickness)
        panel_width = h_w + 10
        panel_height = h_h + 12

        if sub_text:
            (s_w, s_h), _ = cv2.getTextSize(sub_text, font, sub_font_scale, thickness)
            panel_width = max(panel_width, s_w + 10)
            panel_height += s_h + 8

        panel_x1 = sx1
        panel_y1 = max(0, sy1 - panel_height)
        panel_x2 = min(fw, panel_x1 + panel_width)
        panel_y2 = panel_y1 + panel_height

        # Render translucent dark panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x1, panel_y1), (panel_x2, panel_y2), (20, 20, 20), -1)
        # Add colored top border to panel
        cv2.line(overlay, (panel_x1, panel_y1), (panel_x2, panel_y1), color, 2, cv2.LINE_AA)
        
        # Apply translucency
        opacity = 0.85
        cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)

        # Draw Text
        text_y = panel_y1 + h_h + 6
        cv2.putText(frame, header_text, (panel_x1 + 5, text_y), font, header_font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        if sub_text:
            text_y += s_h + 6
            cv2.putText(frame, sub_text, (panel_x1 + 5, text_y), font, sub_font_scale, (200, 255, 255), thickness, cv2.LINE_AA)

    # ==========================================
    # 🚗 SLAVE MODEL DISPATCH HELPERS
    # ==========================================

    def should_dispatch_description(self, track_id: int) -> bool:
        """Check if we should dispatch BLIP description for this track."""
        return track_id not in self.description_dispatched

    def should_dispatch_plate(self, track_id: int, bbox_area: float, frame_count: int) -> bool:
        """
        Check if we should dispatch plate reading for this track.

        Logic: Repeatedly poll the ALPR model across multiple frames while the
        bounding box is large enough. Stop if the plate is locked or already polling.
        """
        if track_id in self.plate_locked:
            return False  # Confirmed and locked
            
        if track_id in self.plate_dispatched:
            return False  # Currently running a thread

        # Allow max 15 attempts to prevent endless polling on unreadable objects
        if len(self.plate_history[track_id]) >= 15:
            return False

        # Store the current best crop
        prev_best = self.best_bbox_area.get(track_id, 0)
        if bbox_area > prev_best:
            self.best_bbox_area[track_id] = bbox_area

        return True

    def should_dispatch_dms(self, track_id: int) -> bool:
        """Check if we should dispatch DMS analysis for this track."""
        return track_id not in self.dms_dispatched

    def get_vehicle_crop(self, frame: np.ndarray, x1, y1, x2, y2) -> Optional[np.ndarray]:
        """Safely crop a vehicle region from the frame."""
        h, w = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if x2 <= x1 or y2 <= y1:
            return None

        return frame[y1:y2, x1:x2].copy()

    # ==========================================
    # 🚀 MAIN ANALYSIS PIPELINE (v2.0)
    # ==========================================

    def analyze_frame(
        self,
        frame: np.ndarray,
        frame_count: int,
        fps: float,
    ) -> FrameResult:
        """
        Process a single video frame through the full pipeline.

        v2.0 Changes:
            - Initializes BEV calibrator on first frame.
            - Uses BEV-projected speed instead of K/bbox_height.
            - Collects slave model results from caches.
            - Returns enriched VehicleInfo list.

        Args:
            frame: Raw BGR frame from cv2.VideoCapture
            frame_count: Current frame number
            fps: Source video FPS

        Returns:
            FrameResult with annotated frame, metrics, and vehicle data.
        """
        if not self._model_loaded or self.model is None:
            self.load_model()

        # --- Initialize BEV calibrator on first frame (CHANGED) ---
        height, width = frame.shape[:2]
        if not self._calibrator_initialized:
            self.calibrator.auto_calibrate(width, height)
            self._calibrator_initialized = True
            logger.info(
                f"BEV calibrator auto-initialized for {width}×{height} frame."
            )

        # Calculate processing FPS
        self._fps_frame_count += 1
        elapsed = time.time() - self._fps_start_time
        if elapsed >= 1.0:
            self._current_fps = self._fps_frame_count / elapsed
            self._fps_frame_count = 0
            self._fps_start_time = time.time()

        current_time_str = time.strftime("%H:%M:%S")

        # Draw lane overlay
        self._draw_lane_overlay(frame, width, height)

        # Draw BEV ROI (subtle yellow trapezoid)
        self.calibrator.draw_roi_overlay(frame, color=(0, 200, 255), thickness=1)

        # Run YOLO tracking (Master model)
        results = self.model.track(
            frame, persist=True,
            classes=VEHICLE_CLASSES,
            verbose=False,
            conf=YOLO_CONFIDENCE,
        )

        current_vehicle_count = 0
        current_frame_speeds = []
        events = []
        vehicles = []

        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids = results[0].boxes.id.cpu().numpy().astype(int)
            classes = results[0].boxes.cls.cpu().numpy().astype(int)
            current_vehicle_count = len(ids)

            for box, track_id, cls_id in zip(boxes, ids, classes):
                x1, y1, x2, y2 = map(int, box)
                x_center = (x1 + x2) / 2.0
                y_center = (y1 + y2) / 2.0
                bbox_height = y2 - y1
                bbox_area = (x2 - x1) * (y2 - y1)

                # Update history
                hist = self.track_history[track_id]
                hist["centers_x"].append(x_center)
                hist["centers_y"].append(y_center)
                hist["heights"].append(bbox_height)
                hist["last_seen_frame"] = frame_count

                # Bound history
                if len(hist["centers_y"]) > HISTORY_LENGTH:
                    hist["centers_x"].pop(0)
                    hist["centers_y"].pop(0)
                    hist["heights"].pop(0)

                # --- Metrics ---
                lane = self.get_lane(x_center, width)
                direction = self.detect_direction(hist["centers_y"])

                # --- CHANGED: BEV-calibrated speed (replaces K/bbox_height) ---
                current_speed = 0.0
                if self.speed_enabled:
                    current_speed = self.compute_speed_bev(
                        hist, x_center, y_center, fps
                    )

                hist["speeds"].append(current_speed)
                if len(hist["speeds"]) > HISTORY_LENGTH:
                    hist["speeds"].pop(0)

                current_frame_speeds.append(current_speed)

                # --- Store best crop for plate reading ---
                if bbox_area > self.best_bbox_area.get(track_id, 0):
                    crop = self.get_vehicle_crop(frame, x1, y1, x2, y2)
                    if crop is not None:
                        self.best_bbox_crop[track_id] = crop

                # --- Behavior Analysis (MAINTAINED) ---
                is_wrong_way = False
                if self.wrong_way_enabled:
                    is_wrong_way = self.check_wrong_way(lane, direction)

                is_sudden_stop = self.check_sudden_stop(
                    current_speed, hist["speeds"][:-1]
                )

                behavior = "NORMAL"
                color = CV_COLOR_NORMAL

                # Retrieve cached slave model results
                vehicle_desc = self.description_cache.get(track_id, "⏳")
                plate_number = self.plate_cache.get(track_id, "—")
                driver_status = self.dms_cache.get(track_id, "N/A")

                if is_wrong_way:
                    behavior = "WRONG WAY"
                    color = CV_COLOR_WRONG_WAY
                    events.append(VehicleEvent(
                        vehicle_id=int(track_id),
                        event_type="WRONG WAY",
                        timestamp=current_time_str,
                        lane=lane,
                        vehicle_desc=vehicle_desc,
                        plate_number=plate_number,
                    ))
                elif is_sudden_stop:
                    behavior = "SUDDEN STOP"
                    color = CV_COLOR_SUDDEN_STOP
                    events.append(VehicleEvent(
                        vehicle_id=int(track_id),
                        event_type="SUDDEN STOP",
                        timestamp=current_time_str,
                        lane=lane,
                        vehicle_desc=vehicle_desc,
                        plate_number=plate_number,
                    ))
                elif current_speed < STOPPED_SPEED_THRESHOLD:
                    behavior = "STOPPED"
                elif current_speed < SLOW_SPEED_THRESHOLD:
                    behavior = "SLOW"

                # Draw vehicle box with enriched labels
                self._draw_vehicle_box(
                    frame, x1, y1, x2, y2, track_id,
                    lane, current_speed, behavior, color,
                    vehicle_desc=vehicle_desc if vehicle_desc != "⏳" else "",
                    plate=plate_number if plate_number != "—" else "",
                )

                # Build VehicleInfo (NEW in v2.0)
                vehicles.append(VehicleInfo(
                    track_id=int(track_id),
                    speed_kmh=current_speed,
                    direction=direction,
                    lane=lane,
                    behavior=behavior,
                    vehicle_desc=vehicle_desc,
                    plate_number=plate_number,
                    driver_status=driver_status,
                    coco_class=int(cls_id),
                ))

        # --- Global metrics ---
        avg_speed = (
            sum(current_frame_speeds) / len(current_frame_speeds)
            if current_frame_speeds else 0.0
        )

        density_status = "LOW"
        if self.density_enabled:
            density_status = self.get_traffic_density(
                current_vehicle_count, avg_speed
            )

        return FrameResult(
            annotated_frame=frame,
            vehicle_count=current_vehicle_count,
            average_speed=round(avg_speed, 1),
            density_status=density_status,
            events=events,
            vehicles=vehicles,
            fps=round(self._current_fps, 1),
            frame_number=frame_count,
        )
