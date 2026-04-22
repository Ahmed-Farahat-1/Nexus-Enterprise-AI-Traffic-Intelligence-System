"""
Bird's-Eye View Calibration Module.

Implements perspective transformation (homography) to convert pixel
coordinates on the road surface to real-world metric coordinates.
This replaces the flawed K/bbox_height speed estimation approach.

How it works:
    1. Define 4 source points forming a trapezoid on the road in the
       original camera view (wider at bottom, narrower at top due to
       perspective foreshortening).
    2. Map them to a rectangle of known real-world dimensions (meters).
    3. Use cv2.getPerspectiveTransform to compute the 3×3 homography.
    4. Any pixel coordinate can then be projected to world-space meters.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List

from utils.constants import (
    BEV_SRC_POINTS_DEFAULT,
    BEV_REAL_WIDTH_METERS,
    BEV_REAL_HEIGHT_METERS,
    SPEED_SMOOTHING_WINDOW,
    SPEED_MAX_PLAUSIBLE,
)


class BirdEyeViewCalibrator:
    """
    Perspective transform calibrator for road-surface distance estimation.

    Converts pixel coordinates from the camera frame into a Bird's-Eye
    View (BEV) coordinate system where Euclidean distances correspond
    to real-world meters.
    """

    def __init__(
        self,
        src_points: Optional[np.ndarray] = None,
        real_width_m: float = BEV_REAL_WIDTH_METERS,
        real_height_m: float = BEV_REAL_HEIGHT_METERS,
    ):
        """
        Args:
            src_points: 4×2 array of source points in pixel space [TL, TR, BR, BL].
                        If None, auto_calibrate() must be called with frame dims.
            real_width_m: Real-world width of the ROI in meters.
            real_height_m: Real-world depth of the ROI in meters.
        """
        self.real_width_m = real_width_m
        self.real_height_m = real_height_m

        # BEV output image dimensions (pixels) — arbitrary, just for visualization
        self._bev_width_px = 400
        self._bev_height_px = 600

        # Destination rectangle in BEV space
        self._dst_points = np.float32([
            [0, 0],                                     # TL
            [self._bev_width_px, 0],                    # TR
            [self._bev_width_px, self._bev_height_px],  # BR
            [0, self._bev_height_px],                   # BL
        ])

        # Pixels-per-meter in BEV space
        self._ppm_x = self._bev_width_px / self.real_width_m
        self._ppm_y = self._bev_height_px / self.real_height_m

        # Homography matrices
        self._M: Optional[np.ndarray] = None       # camera → BEV
        self._M_inv: Optional[np.ndarray] = None   # BEV → camera

        self._calibrated = False

        if src_points is not None:
            self._compute_homography(np.float32(src_points))

    def auto_calibrate(self, frame_width: int, frame_height: int):
        """
        Generate default trapezoidal source points from frame dimensions.

        Assumes a standard highway camera mounted at moderate height
        looking down the road. The trapezoid covers the central road area:
        - Bottom edge: full width at ~90% frame height
        - Top edge: narrower at ~40% frame height (perspective convergence)

        Args:
            frame_width: Video frame width in pixels.
            frame_height: Video frame height in pixels.
        """
        # --- CHANGED: Auto-generate source trapezoid from frame geometry ---
        # Bottom of ROI: wide, near camera
        bottom_y = int(frame_height * 0.90)
        bottom_left_x = int(frame_width * 0.10)
        bottom_right_x = int(frame_width * 0.90)

        # Top of ROI: narrow, far from camera
        top_y = int(frame_height * 0.40)
        top_left_x = int(frame_width * 0.30)
        top_right_x = int(frame_width * 0.70)

        src = np.float32([
            [top_left_x, top_y],         # TL
            [top_right_x, top_y],        # TR
            [bottom_right_x, bottom_y],  # BR
            [bottom_left_x, bottom_y],   # BL
        ])

        self._compute_homography(src)

    def _compute_homography(self, src_points: np.ndarray):
        """Compute the perspective transformation matrix."""
        self._src_points = src_points
        self._M = cv2.getPerspectiveTransform(src_points, self._dst_points)
        self._M_inv = cv2.getPerspectiveTransform(self._dst_points, src_points)
        self._calibrated = True

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def pixel_to_world(self, x_px: float, y_px: float) -> Tuple[float, float]:
        """
        Project a pixel coordinate into the BEV world-coordinate system.

        Returns:
            (x_meters, y_meters) — position in real-world meters.
        """
        if not self._calibrated:
            raise RuntimeError("Calibrator not initialized. Call auto_calibrate() first.")

        # Apply homography to the point
        pt = np.float32([[[x_px, y_px]]])
        transformed = cv2.perspectiveTransform(pt, self._M)
        bev_x, bev_y = transformed[0][0]

        # Convert BEV pixels to meters
        x_m = bev_x / self._ppm_x
        y_m = bev_y / self._ppm_y

        return (x_m, y_m)

    def compute_speed(
        self,
        prev_pos_px: Tuple[float, float],
        curr_pos_px: Tuple[float, float],
        dt_seconds: float,
    ) -> float:
        """
        Compute calibrated speed in km/h from two pixel positions and time delta.

        Args:
            prev_pos_px: (x, y) previous position in pixels.
            curr_pos_px: (x, y) current position in pixels.
            dt_seconds: Time elapsed between the two positions.

        Returns:
            Speed in km/h, clamped to SPEED_MAX_PLAUSIBLE.
        """
        if dt_seconds <= 0:
            return 0.0

        x1_m, y1_m = self.pixel_to_world(*prev_pos_px)
        x2_m, y2_m = self.pixel_to_world(*curr_pos_px)

        # Euclidean distance in meters
        dist_m = np.sqrt((x2_m - x1_m) ** 2 + (y2_m - y1_m) ** 2)

        # Speed: m/s → km/h
        speed_ms = dist_m / dt_seconds
        speed_kmh = speed_ms * 3.6

        # Clamp unrealistic values (caused by tracking glitches)
        return min(round(speed_kmh, 1), SPEED_MAX_PLAUSIBLE)

    def transform_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Warp the full frame to Bird's-Eye View (useful for debugging).

        Returns:
            BEV-warped image of shape (bev_height_px, bev_width_px, 3).
        """
        if not self._calibrated:
            raise RuntimeError("Calibrator not initialized.")

        return cv2.warpPerspective(
            frame, self._M,
            (self._bev_width_px, self._bev_height_px),
        )

    def draw_roi_overlay(self, frame: np.ndarray, color=(0, 255, 255), thickness=2):
        """Draw the calibration ROI trapezoid on the frame for visualization."""
        if not self._calibrated or self._src_points is None:
            return frame

        pts = self._src_points.astype(np.int32).reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=thickness)
        return frame


class SpeedSmoother:
    """
    Exponential Moving Average (EMA) smoother for speed values.

    Reduces frame-to-frame jitter in speed estimates caused by
    bounding box localization noise.
    """

    def __init__(self, window: int = SPEED_SMOOTHING_WINDOW):
        self._alpha = 2.0 / (window + 1)
        self._ema: Optional[float] = None

    def update(self, raw_speed: float) -> float:
        """Feed a raw speed value and return the smoothed speed."""
        if self._ema is None:
            self._ema = raw_speed
        else:
            self._ema = self._alpha * raw_speed + (1 - self._alpha) * self._ema
        return round(self._ema, 1)

    def reset(self):
        self._ema = None
