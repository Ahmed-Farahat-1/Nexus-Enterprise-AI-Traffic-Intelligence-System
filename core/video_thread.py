"""
Video processing thread — Master-Slave architecture (v2.1).

v2.1 Bug Fixes & Features:
    - FIXED: Added session_data dict for persistent vehicle data across frames.
    - FIXED: session_update signal for flicker-free UI table updates.
    - FIXED: Bbox area thresholds for slave model dispatch.
    - FIXED: Robust error handling in slave workers (Unknown/Unreadable fallbacks).
    - NEW: finished_processing signal for end-of-session summary.
    - NEW: Automatic CSV summary export on session end.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │  VideoThread (QThread)                                   │
    │  ├── Master: YOLO track() — every frame                  │
    │  ├── Session Data: Persistent dict[Track_ID] → {...}     │
    │  └── Slaves dispatched to ThreadPoolExecutor:            │
    │       ├── BLIP vehicle description (bbox > 5000px²)      │
    │       ├── YOLO+EasyOCR plate read (bbox > 5000px²)       │
    │       └── CLIP DMS analysis (bbox > 8000px²)             │
    │  Results → session_data → session_update signal → UI     │
    └──────────────────────────────────────────────────────────┘
"""

import csv
import os
import cv2
import time
import logging
import numpy as np
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt6.QtGui import QImage

from core.traffic_analyzer import TrafficAnalyzer, FrameResult
from core.model_registry import ModelRegistry
from utils.constants import (
    SLAVE_THREAD_POOL_WORKERS,
    MIN_BBOX_AREA_FOR_SLAVE,
    MIN_BBOX_AREA_FOR_DMS,
    SUMMARY_CSV_FILENAME,
)

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Video source types."""
    CAMERA = "camera"
    VIDEO_FILE = "video_file"
    IP_CAMERA = "ip_camera"


class VideoThread(QThread):
    """
    Worker thread for video capture and multi-model AI analysis.

    v2.1 Changes:
        - session_data dict persists all vehicle attributes across frames.
        - session_update signal emits complete state for flicker-free UI.
        - finished_processing signal triggers end-of-session summary + CSV.
        - Slave models only dispatched when bbox area exceeds threshold.
        - Robust error handling with "Unknown"/"Unreadable" fallbacks.
    """

    # Signals
    frame_ready = pyqtSignal(QImage, object)     # processed frame + FrameResult
    error_occurred = pyqtSignal(str)             # error message
    source_ended = pyqtSignal()                  # video file ended
    model_loaded = pyqtSignal()                  # YOLO model loaded successfully
    session_update = pyqtSignal(dict, int)       # session_data + current_frame
    finished_processing = pyqtSignal(dict)       # final session_data for summary

    def __init__(self, parent=None):
        super().__init__(parent)
        self.analyzer = TrafficAnalyzer()

        # State
        self._source_type: SourceType = SourceType.CAMERA
        self._source_path: str = ""
        self._running = False
        self._paused = False

        # Threading primitives
        self._mutex = QMutex()
        self._pause_condition = QWaitCondition()

        # Slave model thread pool
        self._slave_pool: ThreadPoolExecutor = None

        # Persistent session data — keyed by Track_ID, survives across frames
        self.session_data: dict = {}

    def set_source(self, source_type: SourceType, source_path: str = ""):
        """Configure the video source before starting."""
        self._source_type = source_type
        self._source_path = source_path

    def pause(self):
        """Pause frame processing."""
        self._mutex.lock()
        self._paused = True
        self._mutex.unlock()

    def resume(self):
        """Resume frame processing."""
        self._mutex.lock()
        self._paused = False
        self._pause_condition.wakeAll()
        self._mutex.unlock()

    def stop(self):
        """Stop the thread gracefully."""
        self._mutex.lock()
        self._running = False
        self._paused = False
        self._pause_condition.wakeAll()
        self._mutex.unlock()

    @property
    def is_paused(self) -> bool:
        return self._paused

    def run(self):
        """
        Main thread loop — Master-Slave pipeline with session persistence.

        v2.1: Added session_data tracking, session_update emission,
        and finished_processing signal on loop exit (both natural
        end-of-stream and manual stop).
        """
        self._running = True
        self._paused = False

        # Load master YOLO model
        try:
            self.analyzer.load_model()
            self.model_loaded.emit()
        except Exception as e:
            self.error_occurred.emit(f"Failed to load YOLO model: {str(e)}")
            return

        # Reset tracking state and session data
        self.analyzer.reset()
        self.session_data = {}

        # Initialize slave thread pool
        self._slave_pool = ThreadPoolExecutor(
            max_workers=SLAVE_THREAD_POOL_WORKERS,
            thread_name_prefix="slave_model",
        )

        # Determine video source
        if self._source_type == SourceType.CAMERA:
            source = 0
        else:
            source = self._source_path

        # Open capture
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            self.error_occurred.emit(
                f"Could not open video source: {source}"
            )
            self._slave_pool.shutdown(wait=False)
            return

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        frame_count = 0
        stream_ended_naturally = False

        while self._running:
            # Handle pause
            self._mutex.lock()
            if self._paused:
                self._pause_condition.wait(self._mutex)
            self._mutex.unlock()

            if not self._running:
                break

            ret, frame = cap.read()
            if not ret:
                stream_ended_naturally = True
                break

            frame_count += 1

            # =============================================
            # MASTER: Run YOLO tracking + BEV speed + behavior
            # =============================================
            try:
                result: FrameResult = self.analyzer.analyze_frame(
                    frame, frame_count, fps
                )
            except Exception as e:
                self.error_occurred.emit(
                    f"Analysis error (frame {frame_count}): {str(e)}"
                )
                continue

            # =============================================
            # SESSION DATA: Update persistent state FIRST
            # (creates entries before slaves access them)
            # =============================================
            self._update_session_data(result)

            # =============================================
            # SLAVE DISPATCH: Non-blocking async model calls
            # (only for vehicles with bbox > area threshold)
            # =============================================
            try:
                self._dispatch_slave_tasks(frame, result)
            except Exception as e:
                logger.warning(f"Slave dispatch error: {e}")

            # =============================================
            # EMIT: Frame to UI + persistent session state
            # =============================================
            rgb_frame = cv2.cvtColor(result.annotated_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(
                rgb_frame.data, w, h, bytes_per_line,
                QImage.Format.Format_RGB888,
            ).copy()  # .copy() to own the data

            self.frame_ready.emit(qt_image, result)
            self.session_update.emit(dict(self.session_data), result.frame_number)

        # =============================================
        # END OF SESSION: Summary + Cleanup
        # =============================================

        # Export CSV and emit summary (fires for BOTH natural end and manual stop)
        if self.session_data:
            try:
                self._export_summary_csv()
            except Exception as e:
                logger.warning(f"CSV export failed: {e}")
            self.finished_processing.emit(dict(self.session_data))

        # Emit source_ended only for natural end-of-stream
        if stream_ended_naturally:
            self.source_ended.emit()

        # Cleanup
        cap.release()

        if self._slave_pool:
            self._slave_pool.shutdown(wait=False, cancel_futures=True)
            self._slave_pool = None

        # Unload heavy models to free memory
        try:
            ModelRegistry().unload_all()
        except Exception:
            pass

    # ==========================================
    # 📊 SESSION DATA PERSISTENCE (v2.1)
    # ==========================================

    def _update_session_data(self, result: FrameResult):
        """
        Update the persistent session_data dictionary from current frame.

        This dict accumulates ALL vehicle data across the entire session.
        Slave model results (desc, plate, DMS) are preserved even after
        a vehicle leaves the frame — this prevents UI data loss.

        Uses incremental average speed (O(1) memory) instead of storing
        all speed samples.
        """
        active_ids = set()

        for v in result.vehicles:
            tid = v.track_id
            active_ids.add(tid)

            if tid not in self.session_data:
                # First time seeing this vehicle — initialize entry
                self.session_data[tid] = {
                    "track_id": tid,
                    "speed_kmh": 0.0,
                    "max_speed_kmh": 0.0,
                    "avg_speed_kmh": 0.0,
                    "_speed_count": 0,
                    "_speed_total": 0.0,
                    "direction": "UNKNOWN",
                    "lane": "UNKNOWN",
                    "behavior": "NORMAL",
                    "vehicle_desc": "⏳",
                    "plate_number": "—",
                    "driver_status": "N/A",
                    "coco_class": v.coco_class,
                    "first_seen_frame": result.frame_number,
                    "last_seen_frame": result.frame_number,
                    "active": True,
                    "had_wrong_way": False,
                    "had_sudden_stop": False,
                }

            entry = self.session_data[tid]

            # Update live metrics
            entry["speed_kmh"] = v.speed_kmh
            entry["max_speed_kmh"] = max(entry["max_speed_kmh"], v.speed_kmh)

            # Incremental average speed (O(1) memory)
            if v.speed_kmh > 0:
                entry["_speed_count"] += 1
                entry["_speed_total"] += v.speed_kmh
                entry["avg_speed_kmh"] = round(
                    entry["_speed_total"] / entry["_speed_count"], 1
                )

            # Only overwrite direction if definitive
            if v.direction != "UNKNOWN":
                entry["direction"] = v.direction

            entry["lane"] = v.lane
            entry["behavior"] = v.behavior
            entry["coco_class"] = v.coco_class
            entry["last_seen_frame"] = result.frame_number
            entry["active"] = True

            # Track behavioral flags (persist even if behavior changes)
            if v.behavior == "WRONG WAY":
                entry["had_wrong_way"] = True
            if v.behavior == "SUDDEN STOP":
                entry["had_sudden_stop"] = True

            # Persist enrichment only if it's a real result (not placeholder)
            if v.vehicle_desc and v.vehicle_desc not in ("⏳", ""):
                entry["vehicle_desc"] = v.vehicle_desc
            if v.plate_number and v.plate_number not in ("—", ""):
                entry["plate_number"] = v.plate_number
            if v.driver_status and v.driver_status not in ("N/A", ""):
                entry["driver_status"] = v.driver_status

        # Mark vehicles no longer visible as inactive
        for tid in self.session_data:
            if tid not in active_ids:
                self.session_data[tid]["active"] = False

    def _export_summary_csv(self):
        """Export session summary to a timestamped CSV in the project directory."""
        if not self.session_data:
            return

        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{SUMMARY_CSV_FILENAME}_{timestamp}.csv"
            project_dir = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
            filepath = os.path.join(project_dir, filename)

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Track ID", "Type & Color", "Plate Number",
                    "Max Speed (km/h)", "Avg Speed (km/h)",
                    "Direction", "Lane", "Last Behavior",
                    "Driver Status", "Wrong Way", "Sudden Stop",
                    "First Frame", "Last Frame",
                ])
                for tid in sorted(self.session_data.keys()):
                    v = self.session_data[tid]
                    writer.writerow([
                        v["track_id"],
                        v["vehicle_desc"],
                        v["plate_number"],
                        v["max_speed_kmh"],
                        v["avg_speed_kmh"],
                        v["direction"],
                        v["lane"],
                        v["behavior"],
                        v["driver_status"],
                        "YES" if v.get("had_wrong_way") else "NO",
                        "YES" if v.get("had_sudden_stop") else "NO",
                        v["first_seen_frame"],
                        v["last_seen_frame"],
                    ])

            logger.info(f"Session summary exported: {filepath}")

        except Exception as e:
            logger.error(f"CSV export failed: {e}")

    # ==========================================
    # 🔧 SLAVE MODEL DISPATCH (v2.1 — area-gated)
    # ==========================================

    def _dispatch_slave_tasks(self, frame: np.ndarray, result: FrameResult):
        """
        Dispatch slave model tasks with bbox area thresholds.

        v2.1 Changes:
            - Only dispatches when bbox_area >= MIN_BBOX_AREA_FOR_SLAVE.
            - DMS requires even larger area (MIN_BBOX_AREA_FOR_DMS).
            - Prevents wasting inference on tiny, unreadable vehicle crops.
        """
        if self._slave_pool is None:
            return

        for vehicle in result.vehicles:
            tid = vehicle.track_id
            x1, y1, x2, y2 = self._get_vehicle_bbox(vehicle, frame)
            bbox_area = (x2 - x1) * (y2 - y1)

            # --- Gate: skip vehicles with bbox too small ---
            if bbox_area < MIN_BBOX_AREA_FOR_SLAVE:
                continue

            # --- 1. Vehicle Description (BLIP) ---
            if self.analyzer.should_dispatch_description(tid):
                crop = self.analyzer.get_vehicle_crop(frame, x1, y1, x2, y2)
                if crop is not None and crop.shape[0] > 30 and crop.shape[1] > 30:
                    self.analyzer.description_dispatched.add(tid)
                    crop_copy = crop.copy()
                    self._slave_pool.submit(
                        self._run_description, tid, crop_copy
                    )

            # --- 2. Plate Reading (YOLO + EasyOCR) ---
            if self.analyzer.should_dispatch_plate(tid, bbox_area, result.frame_number):
                best_crop = self.analyzer.best_bbox_crop.get(tid)
                if best_crop is not None:
                    self.analyzer.plate_dispatched.add(tid)
                    crop_copy = best_crop.copy()
                    self._slave_pool.submit(
                        self._run_plate_read, tid, crop_copy
                    )

            # --- 3. Driver Monitoring (CLIP) — needs larger crop ---
            if bbox_area >= MIN_BBOX_AREA_FOR_DMS:
                if self.analyzer.should_dispatch_dms(tid):
                    crop = self.analyzer.get_vehicle_crop(frame, x1, y1, x2, y2)
                    if crop is not None and crop.shape[0] > 80 and crop.shape[1] > 80:
                        self.analyzer.dms_dispatched.add(tid)
                        crop_copy = crop.copy()
                        self._slave_pool.submit(
                            self._run_dms, tid, crop_copy
                        )

    def _get_vehicle_bbox(self, vehicle, frame):
        """Extract bbox coordinates from VehicleInfo via tracking history."""
        hist = self.analyzer.track_history.get(vehicle.track_id)
        if hist and hist["centers_x"] and hist["centers_y"] and hist["heights"]:
            cx = hist["centers_x"][-1]
            cy = hist["centers_y"][-1]
            bh = hist["heights"][-1]
            bw = bh * 1.2  # Approximate aspect ratio
            x1 = int(cx - bw / 2)
            y1 = int(cy - bh / 2)
            x2 = int(cx + bw / 2)
            y2 = int(cy + bh / 2)
            return x1, y1, x2, y2

        # Fallback — use frame center
        h, w = frame.shape[:2]
        return 0, 0, w, h

    # ==========================================
    # ⚙️ SLAVE MODEL WORKERS (v2.1 — robust error handling)
    # ==========================================
    # These methods run in ThreadPoolExecutor threads.
    # They update BOTH analyzer caches AND session_data directly.
    # Failures return meaningful fallback values, never crash.

    def _run_description(self, track_id: int, crop: np.ndarray):
        """Run BLIP vehicle description in background thread."""
        try:
            from core.vehicle_descriptor import describe_vehicle
            desc = describe_vehicle(crop)
            if not desc:
                desc = "Unknown"
        except Exception as e:
            logger.warning(f"[BLIP] Track {track_id} failed: {e}")
            desc = "Unknown"

        # Write to both caches
        self.analyzer.description_cache[track_id] = desc
        if track_id in self.session_data:
            self.session_data[track_id]["vehicle_desc"] = desc
        logger.debug(f"[BLIP] Track {track_id}: {desc}")

    def _run_plate_read(self, track_id: int, crop: np.ndarray):
        """Run YOLO+EasyOCR plate reading with temporal voting."""
        try:
            from core.plate_reader import read_plate
            import collections
            
            plate = read_plate(crop)
            
            if plate and len(plate) >= 3:
                self.analyzer.plate_history[track_id].append(plate)
                
            reads = self.analyzer.plate_history[track_id]
            
            if not reads:
                result_text = "Unreadable"
            else:
                # Get the most common read (mode)
                most_common = collections.Counter(reads).most_common(1)[0]
                best_plate, count = most_common[0], most_common[1]
                
                # Lock if we have 5 consistent consensus reads
                if count >= 5:
                    self.analyzer.plate_locked.add(track_id)
                    result_text = best_plate
                else:
                    # Append a pending indicator to show it's still voting
                    result_text = f"{best_plate} (?)"

        except Exception as e:
            logger.warning(f"[PLATE] Track {track_id} failed: {e}")
            result_text = "Unreadable"
        finally:
            self.analyzer.plate_dispatched.discard(track_id)

        self.analyzer.plate_cache[track_id] = result_text
        if track_id in self.session_data:
            self.session_data[track_id]["plate_number"] = result_text
        logger.debug(f"[PLATE] Track {track_id}: {result_text}")

    def _run_dms(self, track_id: int, crop: np.ndarray):
        """Run CLIP DMS analysis in background thread."""
        try:
            from core.driver_monitor import analyze_driver
            status = analyze_driver(crop)
            if not status:
                status = "Unknown"
        except Exception as e:
            logger.warning(f"[DMS] Track {track_id} failed: {e}")
            status = "Unknown"

        self.analyzer.dms_cache[track_id] = status
        if track_id in self.session_data:
            self.session_data[track_id]["driver_status"] = status
        logger.debug(f"[DMS] Track {track_id}: {status}")
