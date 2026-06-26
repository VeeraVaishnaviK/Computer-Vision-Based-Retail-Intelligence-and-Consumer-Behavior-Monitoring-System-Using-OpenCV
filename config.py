"""
config.py
=========
Central configuration file for the Retail Intelligence System.
All tunable parameters, file paths, zone definitions, and display
settings are defined here. Modify this file to adapt the system
to different environments, cameras, or store layouts.
"""

import os

# =============================================================================
# PROJECT PATHS
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DB_PATH = os.path.join(DATA_DIR, "retail_intelligence.db")

# =============================================================================
# WEBCAM SETTINGS
# =============================================================================
CAMERA_INDEX = 0          # 0 = built-in webcam, 1 = external USB webcam
FRAME_WIDTH = 640         # Frame width in pixels
FRAME_HEIGHT = 480        # Frame height in pixels
FPS_LIMIT = 30            # Max FPS cap (0 = unlimited)

# =============================================================================
# YOLO DETECTION SETTINGS
# =============================================================================
YOLO_CFG = os.path.join(MODELS_DIR, "yolov4-tiny.cfg")
YOLO_WEIGHTS = os.path.join(MODELS_DIR, "yolov4-tiny.weights")
COCO_NAMES = os.path.join(MODELS_DIR, "coco.names")

CONFIDENCE_THRESHOLD = 0.5   # Minimum detection confidence
NMS_THRESHOLD = 0.4          # Non-Maximum Suppression threshold
INPUT_SIZE = (416, 416)      # YOLO input blob size
PERSON_CLASS_ID = 0          # COCO class index for 'person'

# Detection backend: "yolo" or "hog"
DETECTION_BACKEND = "yolo"

# =============================================================================
# TRACKER SETTINGS
# =============================================================================
MAX_DISAPPEARED = 40    # Frames before a tracked object is deregistered
MAX_DISTANCE = 80       # Max Euclidean pixel distance for centroid matching

# =============================================================================
# COUNTER SETTINGS — Entry/Exit Lines
# =============================================================================
# Lines are horizontal, spanning the full frame width.
# A person crossing downward past ENTRY_LINE_Y is counted as ENTRY.
# A person crossing upward past EXIT_LINE_Y is counted as EXIT.
ENTRY_LINE_Y = 400
EXIT_LINE_Y = 420
LINE_CROSSING_MARGIN = 5   # Pixel tolerance for line crossing detection

# =============================================================================
# VIRTUAL STORE ZONE DEFINITIONS — (x1, y1, x2, y2)
# =============================================================================
ZONES = {
    "Electronics": (20, 50, 300, 230),
    "Grocery":     (330, 50, 620, 230),
    "Fashion":     (20, 260, 300, 440),
    "Billing":     (330, 260, 620, 440),
}

# =============================================================================
# QUEUE & CROWD SETTINGS
# =============================================================================
QUEUE_ROI = ZONES["Billing"]      # Billing zone doubles as queue ROI
CROWD_THRESHOLDS = {
    "LOW": 2,
    "MEDIUM": 4,
    "HIGH": 6,
    "CRITICAL": 8,
}
AVG_SERVICE_TIME = 30             # Estimated seconds per customer served

# =============================================================================
# DISPLAY COLORS — BGR format (OpenCV standard)
# =============================================================================
ZONE_COLORS = {
    "Electronics": (255, 165, 0),    # Orange
    "Grocery":     (0, 200, 0),      # Green
    "Fashion":     (255, 0, 255),    # Magenta
    "Billing":     (0, 255, 255),    # Yellow
}

BBOX_COLOR = (0, 255, 0)            # Green bounding boxes
TRAIL_COLOR = (255, 255, 0)         # Cyan movement trails
ENTRY_LINE_COLOR = (0, 255, 0)      # Green entry line
EXIT_LINE_COLOR = (0, 0, 255)       # Red exit line
TEXT_COLOR = (255, 255, 255)        # White text
PANEL_BG_COLOR = (40, 40, 40)      # Dark gray info panel
ALERT_COLOR = (0, 0, 255)          # Red for alerts

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================
FONT_SCALE = 0.55
FONT_THICKNESS = 1
INFO_PANEL_WIDTH = 280              # Width of the right-side info panel

# =============================================================================
# CSV LOG FILE NAMES
# =============================================================================
VISITOR_LOG = "visitor_log.csv"
MOVEMENT_LOG = "movement_log.csv"
BEHAVIOR_LOG = "behavior_log.csv"
QUEUE_LOG = "queue_log.csv"

# =============================================================================
# HEATMAP SETTINGS
# =============================================================================
HEATMAP_RESOLUTION = (FRAME_HEIGHT, FRAME_WIDTH)   # (rows, cols)
HEATMAP_COLORMAP = 11               # cv2.COLORMAP_JET = 11

# =============================================================================
# ENSURE DATA DIRECTORIES EXIST
# =============================================================================
for _dir in [DATA_DIR, LOGS_DIR, REPORTS_DIR, MODELS_DIR]:
    os.makedirs(_dir, exist_ok=True)
