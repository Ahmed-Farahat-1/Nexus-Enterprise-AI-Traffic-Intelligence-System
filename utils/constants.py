"""
Constants and configuration for the Traffic Intelligence System.

Upgraded with Bird's-Eye View calibration parameters, multi-model
pipeline settings, and expanded UI constants.
"""

# ==========================================
# ⚙️ AI MODEL CONFIGURATION
# ==========================================
YOLO_MODEL = "yolov8n.pt"  # Nano model for real-time speed
YOLO_CONFIDENCE = 0.3
VEHICLE_CLASSES = [2, 3, 5, 7]  # COCO: car, motorcycle, bus, truck

# COCO class name mapping for display
COCO_CLASS_NAMES = {
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
}

# ==========================================
# 📏 BIRD'S-EYE VIEW CALIBRATION
# ==========================================
# Default source points are auto-generated from frame dimensions
# if BEV_SRC_POINTS_DEFAULT is None. Override with 4 pixel coords
# [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] in TL, TR, BR, BL order.
BEV_SRC_POINTS_DEFAULT = None
BEV_REAL_WIDTH_METERS = 7.0    # Standard 2-lane road width
BEV_REAL_HEIGHT_METERS = 40.0  # Depth of the ROI in meters

# Vehicle class average real-world lengths (meters) for fallback
VEHICLE_REAL_LENGTHS = {
    2: 4.5,   # car
    3: 2.0,   # motorcycle
    5: 12.0,  # bus
    7: 8.0,   # truck
}

# ==========================================
# 📏 TRACKING & SPEED CONFIGURATION
# ==========================================
HISTORY_LENGTH = 30  # Frames to keep in per-vehicle history (increased for BEV)
SPEED_FRAME_DIFF = 5   # Compare positions across N frames
DIRECTION_FRAME_DIFF = 5
DIRECTION_THRESHOLD = 5  # Pixel movement threshold to confirm direction

SPEED_SMOOTHING_WINDOW = 5    # EMA window for speed smoothing
SPEED_MAX_PLAUSIBLE = 200.0   # km/h — clamp unrealistic values

# ==========================================
# 🚦 TRAFFIC DENSITY THRESHOLDS
# ==========================================
DENSITY_JAM_VEHICLES = 15
DENSITY_JAM_SPEED = 10
DENSITY_HIGH_VEHICLES = 10
DENSITY_MEDIUM_VEHICLES = 5

# ==========================================
# 🛑 BEHAVIOR DETECTION THRESHOLDS
# ==========================================
SUDDEN_STOP_HIGH_SPEED = 20.0  # km/h — previous speed must exceed this
SUDDEN_STOP_LOW_SPEED = 3.0    # km/h — current speed must be below this
SLOW_SPEED_THRESHOLD = 10.0    # km/h
STOPPED_SPEED_THRESHOLD = 3.0  # km/h

# ==========================================
# 🔄 TRAFFIC DIRECTION MODES
# ==========================================
DIRECTION_MODE_STANDARD = "standard"   # LEFT→DOWN, RIGHT→UP
DIRECTION_MODE_REVERSED = "reversed"   # LEFT→UP, RIGHT→DOWN

DIRECTION_MODE_LABELS = {
    DIRECTION_MODE_STANDARD: "Standard (Left ↓, Right ↑)",
    DIRECTION_MODE_REVERSED: "Reversed (Left ↑, Right ↓)",
}

DIRECTION_RULES = {
    DIRECTION_MODE_STANDARD: {"LEFT": "DOWN", "RIGHT": "UP"},
    DIRECTION_MODE_REVERSED: {"LEFT": "UP",   "RIGHT": "DOWN"},
}

# ==========================================
# 🤖 MULTI-MODEL PIPELINE SETTINGS
# ==========================================
# BLIP vehicle description
BLIP_MODEL_NAME = "Salesforce/blip-image-captioning-base"
BLIP_MAX_TOKENS = 20

# Plate detection
PLATE_YOLO_MODEL = "keremberke/yolov8n-license-plate-detection"
PLATE_CONFIDENCE = 0.4

# EasyOCR
OCR_LANGUAGES = ["en"]

# Driver Monitoring (CLIP zero-shot)
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"
DMS_MIN_CROP_SIZE = 80  # Minimum windshield crop size in px
DMS_CONFIDENCE_THRESHOLD = 0.55  # Below this → report N/A

# Slave model dispatch
PLATE_READ_PATIENCE_FRAMES = 15  # Frames after max bbox to trigger plate read
SLAVE_THREAD_POOL_WORKERS = 2    # Max concurrent slave model workers
MIN_BBOX_AREA_FOR_SLAVE = 5000    # Min bbox area (px²) to dispatch BLIP/OCR
MIN_BBOX_AREA_FOR_DMS = 8000      # DMS needs larger crop for reliability
VEHICLE_ACTIVE_TIMEOUT_FRAMES = 90  # Keep vehicle in table ~3s after leaving

# Summary export
SUMMARY_CSV_FILENAME = "session_summary"

# ==========================================
# 🎨 COLORS — OpenCV (BGR)
# ==========================================
CV_COLOR_NORMAL = (0, 255, 0)        # Green
CV_COLOR_WRONG_WAY = (0, 0, 255)     # Red
CV_COLOR_SUDDEN_STOP = (0, 165, 255) # Orange
CV_COLOR_TEXT = (255, 255, 255)      # White
CV_COLOR_LANE_LINE = (255, 255, 255) # White
CV_COLOR_OVERLAY_BG = (0, 0, 0)     # Black
CV_COLOR_PLATE = (255, 200, 0)       # Cyan-ish for plate boxes

# ==========================================
# 🎨 COLORS — Qt (Hex)
# ==========================================
# Main theme
THEME_BG_PRIMARY = "#0d1117"
THEME_BG_SECONDARY = "#161b22"
THEME_BG_TERTIARY = "#1c2333"
THEME_BG_CARD = "#21262d"
THEME_BORDER = "#30363d"
THEME_BORDER_LIGHT = "#3d444d"

# Text
THEME_TEXT_PRIMARY = "#e6edf3"
THEME_TEXT_SECONDARY = "#8b949e"
THEME_TEXT_MUTED = "#6e7681"

# Accents
THEME_ACCENT = "#58a6ff"
THEME_ACCENT_HOVER = "#79c0ff"
THEME_SUCCESS = "#3fb950"
THEME_SUCCESS_HOVER = "#56d364"
THEME_WARNING = "#d29922"
THEME_DANGER = "#f85149"
THEME_DANGER_HOVER = "#ff7b72"
THEME_INFO = "#39d2c0"

# Status colors
COLOR_DENSITY_LOW = "#3fb950"
COLOR_DENSITY_MEDIUM = "#d29922"
COLOR_DENSITY_HIGH = "#f0883e"
COLOR_DENSITY_JAM = "#f85149"

# ==========================================
# 📊 CHART CONFIGURATION
# ==========================================
CHART_MAX_POINTS = 300
CHART_WINDOW_SECONDS = 60
CHART_BG_COLOR = "#0d1117"
CHART_LINE_VEHICLE = "#58a6ff"
CHART_LINE_SPEED = "#3fb950"
CHART_LINE_DENSITY = "#d29922"
CHART_GRID_COLOR = "#21262d"
CHART_AXIS_COLOR = "#8b949e"

# ==========================================
# 📋 EVENT LOG CONFIGURATION
# ==========================================
MAX_EVENT_LOG_ROWS = 200

# ==========================================
# 🖥️ UI CONFIGURATION
# ==========================================
APP_TITLE = "Traffic Intelligence System"
WINDOW_MIN_WIDTH = 1280
WINDOW_MIN_HEIGHT = 720
VIDEO_PANEL_RATIO = 0.65
CONTROL_PANEL_RATIO = 0.35

# Font
FONT_FAMILY = "Segoe UI"
FONT_SIZE_NORMAL = 11
FONT_SIZE_SMALL = 9
FONT_SIZE_LARGE = 14
FONT_SIZE_TITLE = 18
FONT_SIZE_METRIC = 28
