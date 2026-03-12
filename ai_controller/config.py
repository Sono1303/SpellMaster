"""
Configuration Module - Spell Master Global Constants
Centralized configuration for all game parameters, paths, and visual settings
"""

from pathlib import Path
import cv2

# ============================================================================
# PROJECT PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
AI_CONTROLLER_DIR = Path(__file__).parent

# Model paths
MODEL_DIR = AI_CONTROLLER_DIR / "data" / "models"
MODEL_PATH = MODEL_DIR / "best_spell_model.pkl"

# Asset paths
ASSETS_DIR = AI_CONTROLLER_DIR / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
SPRITE_FIREBALL = SPRITES_DIR / "fireball.png"
SPRITE_ICE = SPRITES_DIR / "ice.png"
SPRITE_LIGHTNING = SPRITES_DIR / "lightning.png"

# ============================================================================
# WINDOW CONFIGURATION
# ============================================================================

# Video capture settings
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Window names
WINDOW_GAMEPLAY = "Ignite: Spell Master - Gameplay"
WINDOW_DEBUG = "Debug Console - AI Recognition"

# ============================================================================
# COLOR SCHEME (BGR Format - OpenCV Standard)
# ============================================================================

# Basic colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (0, 0, 255)
COLOR_GREEN = (0, 255, 0)
COLOR_BLUE = (255, 0, 0)
COLOR_CYAN = (255, 255, 0)
COLOR_YELLOW = (0, 255, 255)
COLOR_PURPLE = (255, 0, 255)

# HP Bar - Red
COLOR_HP = (0, 0, 255)
COLOR_HP_BG = (50, 50, 50)
COLOR_HP_BORDER = (200, 200, 200)

# MP Bar - Blue
COLOR_MP = (255, 0, 0)
COLOR_MP_BG = (50, 50, 50)
COLOR_MP_BORDER = (200, 200, 200)

# State colors
COLOR_IDLE = (0, 255, 0)          # Green
COLOR_CHANTING = (0, 165, 255)    # Orange
COLOR_ACTIVATED = (0, 255, 255)   # Yellow
COLOR_EXECUTING = (255, 0, 0)     # Bright Blue
COLOR_COOLDOWN = (200, 100, 0)    # Dark Blue

# UI Elements
COLOR_TEXT_PRIMARY = (255, 255, 255)    # White
COLOR_TEXT_SECONDARY = (200, 200, 200)  # Light gray
COLOR_TEXT_ERROR = (0, 0, 255)          # Red
COLOR_TEXT_SUCCESS = (0, 255, 0)        # Green

# VFX/Effects
COLOR_FIREBALL_RED = (0, 0, 255)        # Red
COLOR_FIREBALL_ORANGE = (0, 165, 255)   # Orange
COLOR_FIREBALL_YELLOW = (0, 255, 255)   # Yellow

COLOR_ICE_CYAN = (255, 255, 0)          # Cyan
COLOR_ICE_WHITE = (255, 255, 255)       # White

COLOR_LIGHTNING_WHITE = (255, 255, 255) # White
COLOR_LIGHTNING_CYAN = (255, 255, 0)    # Cyan

# Debug UI
COLOR_DEBUG_BG = (0, 0, 0)              # Black
COLOR_DEBUG_BORDER = (200, 200, 200)    # Gray
COLOR_DEBUG_TEXT = (0, 255, 0)          # Green

# Bounding box colors for hand detection
COLOR_BBOX_HAND = (0, 255, 0)           # Green
COLOR_BBOX_HIGHLIGHT = (0, 255, 255)    # Yellow

# ============================================================================
# SPELL RECOGNITION CONFIGURATION
# ============================================================================

# Confidence threshold for spell detection (0.0 - 1.0)
CONFIDENCE_THRESHOLD = 0.80  # 80% confidence required

# Hand detection requirements
REQUIRED_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.4

# Model complexity (0=lite, 1=full)
MEDIAPIPE_MODEL_COMPLEXITY = 1

# ============================================================================
# SPELL CASTING PARAMETERS
# ============================================================================

# Chanting duration (seconds)
CHANT_DURATION = 1.5

# Convert to frames (at 30 FPS)
CHANT_THRESHOLD_FRAMES = int(CHANT_DURATION * 30)  # ~45 frames

# Spell cooldown (seconds between casts)
SPELL_COOLDOWN = 5.0
COOLDOWN_FRAMES = int(SPELL_COOLDOWN * 30)  # ~150 frames

# MP cost per spell
MP_COST_PER_SPELL = 25

# ============================================================================
# GAME STATE PARAMETERS
# ============================================================================

# Initial values
INITIAL_HP = 100
INITIAL_MP = 100
MAX_HP = 100
MAX_MP = 100

# Spell names
SPELL_FIREBALL = "Tiger"
SPELL_ICE = "Dragon"
SPELL_LIGHTNING = "Ox"

SPELL_NAMES = [SPELL_FIREBALL, SPELL_ICE, SPELL_LIGHTNING]

# Spell to VFX mapping
SPELL_TO_VFX = {
    'Fire': 'Fire',
    'Water': 'Water',
    'Air': 'Air',
    'Earth': 'Fire',
    'Tiger': 'Fire',
    'Fireball': 'Fire',
    'Dragon': 'Water',
    'Ice': 'Water',
    'Ox': 'Air',
    'Lightning': 'Air',
}

# ============================================================================
# UI CONFIGURATION
# ============================================================================

# Status bar dimensions (pixels)
STATUS_BAR_WIDTH = 200
STATUS_BAR_HEIGHT = 20
STATUS_BAR_PADDING = 15
STATUS_BAR_SPACING = 10
STATUS_BAR_THICKNESS = 2

# HUD elements
HUD_CORNER_RADIUS = 10      # Corner radius for HUD backgrounds
BAR_HEIGHT = 20             # Height of progress/status bars
BAR_PADDING = 15            # Padding around bars
BAR_BORDER_WIDTH = 2        # Border thickness
HUD_ALPHA = 0.8             # HUD background transparency (0-1)

# Font settings
FONT_FACE = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.6
FONT_THICKNESS = 1
FONT = "cv2.FONT_HERSHEY_SIMPLEX"
FONT_SIZE_NORMAL = 0.6
FONT_SIZE_LARGE = 0.8
FONT_SIZE_HUGE = 1.2
FONT_THICKNESS_NORMAL = 1
FONT_THICKNESS_BOLD = 2
FONT_THICKNESS_EXTRA = 3

# Gesture icon configuration
GESTURE_ICONS = ['Fireball', 'Ice', 'Lightning']
GESTURE_ICON_SIZE = 40
GESTURE_ICON_OFFSET_Y = 60  # Distance from bottom

# Progress circle
PROGRESS_CIRCLE_RADIUS = 30
PROGRESS_CIRCLE_THICKNESS = 3

# ============================================================================
# VFX CONFIGURATION
# ============================================================================

# Effect durations (frames)
FIREBALL_DURATION = 60
ICE_DURATION = 60
LIGHTNING_DURATION = 60

# Sprite animation settings
SPRITE_FRAME_SKIP = 2      # Skip N frames per animation frame
SPRITE_SCALE = 1.5         # Scale factor for sprites

# Effect rendering
EFFECT_ALPHA = 0.6         # Base alpha for effects

# ============================================================================
# LANDMARK SMOOTHING
# ============================================================================

# Landmark smoothing factor (exponential moving average)
SMOOTHING_FACTOR = 0.6

# Hand stability checks
HAND_COUNT_STABLE_THRESHOLD = 2

# ============================================================================
# DEBUG SETTINGS
# ============================================================================

# Debug mode flag (render landmarks and debug info)
DEBUG_MODE = False

# Verbose logging
VERBOSE_MODE = False

# Show FPS counter
SHOW_FPS = True

# Show hand landmarks
SHOW_LANDMARKS = False

# Show bounding boxes
SHOW_BOUNDING_BOXES = True

# Show spell state
SHOW_STATE_INDICATOR = True

# ============================================================================
# PERFORMANCE TUNING
# ============================================================================

# Frame rate target
TARGET_FPS = 30

# Skip frames for optimization
FRAME_SKIP = 1  # Process every N frames

# Max concurrent effects
MAX_CONCURRENT_EFFECTS = 3

# ============================================================================
# KEYBOARD SHORTCUTS
# ============================================================================

KEY_QUIT = 'q'
KEY_DEBUG = 'd'
KEY_VERBOSE = 'v'
KEY_SCREENSHOT = 's'

# Debug spell casting keys
KEY_SPELL_1 = '1'  # Fireball (Tiger)
KEY_SPELL_2 = '2'  # Ice (Dragon)
KEY_SPELL_3 = '3'  # Lightning (Ox)

# ============================================================================
# LANDMARK REFERENCE INDICES
# ============================================================================

# MediaPipe hand landmark indices
LANDMARK_WRIST = 0
LANDMARK_PALM = 9  # Palm center
LANDMARK_THUMB_TIP = 4
LANDMARK_INDEX_TIP = 8
LANDMARK_MIDDLE_TIP = 12
LANDMARK_RING_TIP = 16
LANDMARK_PINKY_TIP = 20

# Total landmarks per hand
LANDMARKS_PER_HAND = 21
TOTAL_LANDMARKS_TWO_HANDS = LANDMARKS_PER_HAND * 2

# Feature vector size (normalized coordinates)
FEATURE_VECTOR_SIZE = TOTAL_LANDMARKS_TWO_HANDS * 2  # x, y per landmark

# ============================================================================
# LOGGING & MESSAGES
# ============================================================================

# Log levels
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"

# Default log level
DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO

# ============================================================================
# ANIMATION & TIMING
# ============================================================================

# Single hand warning duration
SINGLE_HAND_WARNING_FRAMES = 60

# Prediction hold (frames to hold prediction after gesture lost)
PREDICTION_HOLD_COUNT = 5

# Countdown animation
COUNTDOWN_TOTAL_FRAMES = 30

# ============================================================================
# FILE FORMATS & EXTENSIONS
# ============================================================================

# Model file extension
MODEL_EXTENSION = ".pkl"

# Supported image formats
IMAGE_FORMATS = [".png", ".jpg", ".jpeg", ".bmp"]

# Video formats
VIDEO_FORMATS = [".mp4", ".avi", ".mov"]

# ============================================================================
# APPLICATION INFO
# ============================================================================

APP_NAME = "Ignite: Spell Master"
APP_VERSION = "2.0.0"
APP_AUTHOR = "AI-2026 Team"
APP_DESCRIPTION = "Real-time Hand Gesture Spell Recognition with Dual-Window Display"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_color_by_state(state):
    """
    Get color for spell state.
    
    Args:
        state: Spell state string (IDLE, CHANTING, ACTIVATED, EXECUTING, COOLDOWN)
    
    Returns:
        BGR color tuple
    """
    state_colors = {
        'IDLE': COLOR_IDLE,
        'CHANTING': COLOR_CHANTING,
        'ACTIVATED': COLOR_ACTIVATED,
        'EXECUTING': COLOR_EXECUTING,
        'COOLDOWN': COLOR_COOLDOWN,
    }
    return state_colors.get(state, COLOR_IDLE)


def validate_paths():
    """
    Validate that all required paths exist.
    
    Returns:
        Dictionary of validation results
    """
    paths_to_check = {
        'MODEL': MODEL_PATH,
        'ASSETS': ASSETS_DIR,
        'SPRITES': SPRITES_DIR,
    }
    
    results = {}
    for path_name, path in paths_to_check.items():
        results[path_name] = path.exists()
    
    return results


def get_model_path():
    """Get the full path to the trained model."""
    return str(MODEL_PATH)


def get_sprites_dir():
    """Get the full path to sprites directory."""
    return str(SPRITES_DIR)


def get_window_resolution():
    """Get window resolution as tuple (width, height)."""
    return (WINDOW_WIDTH, WINDOW_HEIGHT)


def get_chant_threshold_frames():
    """Get chant threshold in frames based on FPS."""
    return CHANT_THRESHOLD_FRAMES


def get_cooldown_frames():
    """Get cooldown duration in frames based on FPS."""
    return COOLDOWN_FRAMES
