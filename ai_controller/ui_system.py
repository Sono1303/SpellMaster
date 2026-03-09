"""
UI System Module - Handles all UI rendering including HUD, status bars, and bounding boxes.

This module provides the UIRenderer class for rendering game UI elements such as:
- Status bars (HP/MP) with visual effects
- Bounding boxes for hand detection
- HUD overlays and text information
- Debug information display
"""

import cv2
import numpy as np
from config import (
    # Colors (BGR format)
    COLOR_HP,
    COLOR_MP,
    COLOR_WHITE,
    COLOR_BLACK,
    COLOR_YELLOW,
    COLOR_RED,
    COLOR_GREEN,
    COLOR_CYAN,
    COLOR_PURPLE,
    
    # Window settings
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    
    # UI settings
    HUD_CORNER_RADIUS,
    BAR_HEIGHT,
    BAR_PADDING,
    BAR_BORDER_WIDTH,
    HUD_ALPHA,
    
    # Text settings
    FONT_FACE,
    FONT_SCALE,
    FONT_THICKNESS,
)


class UIRenderer:
    """
    Renders user interface elements on video frames.
    
    Handles status bars, bounding boxes, HUD overlays, and debug information.
    """
    
    def __init__(self, frame_width=WINDOW_WIDTH, frame_height=WINDOW_HEIGHT):
        """
        Initialize UIRenderer.
        
        Args:
            frame_width: Frame width in pixels (default: 1280)
            frame_height: Frame height in pixels (default: 720)
        """
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.font_face = FONT_FACE
        self.font_scale = FONT_SCALE
        self.font_thickness = FONT_THICKNESS
    
    def draw_status_bars(self, frame, hp_ratio, mp_ratio, x=20, y=20, bar_width=200):
        """
        Draw HP and MP status bars with visual styling.
        
        Args:
            frame: Input frame (modified in-place)
            hp_ratio: HP ratio (0.0 to 1.0)
            mp_ratio: MP ratio (0.0 to 1.0)
            x: Starting X position (default: 20)
            y: Starting Y position (default: 20)
            bar_width: Width of each bar (default: 200)
        
        Returns:
            Modified frame
        """
        # Clamp ratios to valid range
        hp_ratio = max(0.0, min(1.0, hp_ratio))
        mp_ratio = max(0.0, min(1.0, mp_ratio))
        
        bar_height = BAR_HEIGHT
        padding = BAR_PADDING
        border_width = BAR_BORDER_WIDTH
        
        # === Draw HP Bar ===
        hp_y = y
        
        # HP background (dark red)
        cv2.rectangle(frame, (x, hp_y), (x + bar_width, hp_y + bar_height),
                     (50, 50, 100), -1)
        
        # HP fill
        hp_fill_width = int(bar_width * hp_ratio)
        cv2.rectangle(frame, (x, hp_y), (x + hp_fill_width, hp_y + bar_height),
                     COLOR_HP, -1)
        
        # HP border
        cv2.rectangle(frame, (x, hp_y), (x + bar_width, hp_y + bar_height),
                     COLOR_WHITE, border_width)
        
        # HP label
        cv2.putText(frame, "HP", (x + 5, hp_y + bar_height - 5),
                   self.font_face, 0.5, COLOR_WHITE, 1)
        
        # HP percentage
        hp_text = f"{int(hp_ratio * 100)}%"
        text_size = cv2.getTextSize(hp_text, self.font_face, 0.5, 1)[0]
        cv2.putText(frame, hp_text, (x + bar_width - text_size[0] - 5, hp_y + bar_height - 5),
                   self.font_face, 0.5, COLOR_WHITE, 1)
        
        # === Draw MP Bar ===
        mp_y = hp_y + bar_height + padding
        
        # MP background (dark blue)
        cv2.rectangle(frame, (x, mp_y), (x + bar_width, mp_y + bar_height),
                     (100, 50, 50), -1)
        
        # MP fill
        mp_fill_width = int(bar_width * mp_ratio)
        cv2.rectangle(frame, (x, mp_y), (x + mp_fill_width, mp_y + bar_height),
                     COLOR_MP, -1)
        
        # MP border
        cv2.rectangle(frame, (x, mp_y), (x + bar_width, mp_y + bar_height),
                     COLOR_WHITE, border_width)
        
        # MP label
        cv2.putText(frame, "MP", (x + 5, mp_y + bar_height - 5),
                   self.font_face, 0.5, COLOR_WHITE, 1)
        
        # MP percentage
        mp_text = f"{int(mp_ratio * 100)}%"
        text_size = cv2.getTextSize(mp_text, self.font_face, 0.5, 1)[0]
        cv2.putText(frame, mp_text, (x + bar_width - text_size[0] - 5, mp_y + bar_height - 5),
                   self.font_face, 0.5, COLOR_WHITE, 1)
        
        return frame
    
    def draw_bounding_box(self, frame, hand_detections=None, bboxes=None,
                         merge_hands=False, color=COLOR_GREEN, thickness=2):
        """
        Draw bounding box(es) for hand detection.
        
        Can draw individual boxes for each hand or merge both hands into a single box.
        
        Args:
            frame: Input frame (modified in-place)
            hand_detections: List of hand detection results (alternative to bboxes)
            bboxes: List of bounding boxes as (x1, y1, x2, y2) tuples
            merge_hands: If True, merge all boxes into one encompassing box
            color: Box color in BGR format (default: GREEN)
            thickness: Box line thickness (default: 2)
        
        Returns:
            Modified frame
        """
        if bboxes is None or len(bboxes) == 0:
            return frame
        
        # Validate bboxes format
        if not isinstance(bboxes, list):
            bboxes = list(bboxes)
        
        if merge_hands and len(bboxes) > 1:
            # Merge all bounding boxes into one encompassing box
            x1_min = min(bbox[0] for bbox in bboxes)
            y1_min = min(bbox[1] for bbox in bboxes)
            x2_max = max(bbox[2] for bbox in bboxes)
            y2_max = max(bbox[3] for bbox in bboxes)
            
            # Add padding
            padding = 5
            x1_min = max(0, x1_min - padding)
            y1_min = max(0, y1_min - padding)
            x2_max = min(self.frame_width, x2_max + padding)
            y2_max = min(self.frame_height, y2_max + padding)
            
            # Draw merged box
            cv2.rectangle(frame, (x1_min, y1_min), (x2_max, y2_max),
                         color, thickness)
            
            # Draw corner indicators
            corner_len = 20
            cv2.line(frame, (x1_min, y1_min), (x1_min + corner_len, y1_min),
                    color, thickness)
            cv2.line(frame, (x1_min, y1_min), (x1_min, y1_min + corner_len),
                    color, thickness)
            
            cv2.line(frame, (x2_max, y1_min), (x2_max - corner_len, y1_min),
                    color, thickness)
            cv2.line(frame, (x2_max, y1_min), (x2_max, y1_min + corner_len),
                    color, thickness)
            
            cv2.line(frame, (x1_min, y2_max), (x1_min + corner_len, y2_max),
                    color, thickness)
            cv2.line(frame, (x1_min, y2_max), (x1_min, y2_max - corner_len),
                    color, thickness)
            
            cv2.line(frame, (x2_max, y2_max), (x2_max - corner_len, y2_max),
                    color, thickness)
            cv2.line(frame, (x2_max, y2_max), (x2_max, y2_max - corner_len),
                    color, thickness)
        else:
            # Draw individual boxes for each hand
            for i, bbox in enumerate(bboxes):
                x1, y1, x2, y2 = bbox
                
                # Clamp coordinates
                x1 = max(0, min(self.frame_width, int(x1)))
                y1 = max(0, min(self.frame_height, int(y1)))
                x2 = max(0, min(self.frame_width, int(x2)))
                y2 = max(0, min(self.frame_height, int(y2)))
                
                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                
                # Draw hand label
                label = f"Hand {i + 1}"
                cv2.putText(frame, label, (x1 + 5, y1 - 5),
                           self.font_face, 0.5, color, 1)
        
        return frame
    
    def draw_gesture_hint(self, frame, gesture_name, position="top-center"):
        """
        Draw current gesture/spell name hint on the frame.
        
        Args:
            frame: Input frame (modified in-place)
            gesture_name: Name of the detected gesture/spell
            position: Display position - "top-center", "top-left", "top-right" (default: "top-center")
        
        Returns:
            Modified frame
        """
        font_scale = 1.2
        font_thickness = 2
        color = COLOR_YELLOW
        
        # Get text size
        text_size = cv2.getTextSize(gesture_name, self.font_face, font_scale, font_thickness)[0]
        
        # Calculate position
        if position == "top-center":
            x = (self.frame_width - text_size[0]) // 2
            y = 40
        elif position == "top-left":
            x = 20
            y = 40
        elif position == "top-right":
            x = self.frame_width - text_size[0] - 20
            y = 40
        else:
            x = (self.frame_width - text_size[0]) // 2
            y = 40
        
        # Draw background
        padding = 10
        cv2.rectangle(frame, (x - padding, y - text_size[1] - padding),
                     (x + text_size[0] + padding, y + padding),
                     COLOR_BLACK, -1)
        
        # Draw border
        cv2.rectangle(frame, (x - padding, y - text_size[1] - padding),
                     (x + text_size[0] + padding, y + padding),
                     color, 2)
        
        # Draw text
        cv2.putText(frame, gesture_name, (x, y),
                   self.font_face, font_scale, color, font_thickness)
        
        return frame
    
    def draw_landmarks(self, frame, landmarks, color=COLOR_GREEN, radius=4, thickness=2):
        """
        Draw hand landmarks on the frame.
        
        Args:
            frame: Input frame (modified in-place)
            landmarks: List of (x, y) landmark positions (normalized to frame size)
            color: Landmark color in BGR format (default: GREEN)
            radius: Landmark circle radius (default: 4)
            thickness: Line thickness (default: 2)
        
        Returns:
            Modified frame
        """
        if landmarks is None or len(landmarks) == 0:
            return frame
        
        for i, (x, y) in enumerate(landmarks):
            # Denormalize if coordinates are between 0 and 1
            if x <= 1.0 and y <= 1.0:
                px = int(x * self.frame_width)
                py = int(y * self.frame_height)
            else:
                px = int(x)
                py = int(y)
            
            # Clamp to frame bounds
            px = max(0, min(self.frame_width, px))
            py = max(0, min(self.frame_height, py))
            
            # Draw landmark circle
            cv2.circle(frame, (px, py), radius, color, -1)
            
            # Draw landmark index
            cv2.putText(frame, str(i), (px + 5, py - 5),
                       self.font_face, 0.3, color, 1)
        
        return frame
    
    def draw_connections(self, frame, landmarks, connections, color=COLOR_CYAN, thickness=2):
        """
        Draw connections between landmarks (skeleton lines).
        
        Args:
            frame: Input frame (modified in-place)
            landmarks: List of (x, y) landmark positions
            connections: List of (start_idx, end_idx) pairs
            color: Connection color in BGR format (default: CYAN)
            thickness: Line thickness (default: 2)
        
        Returns:
            Modified frame
        """
        if landmarks is None or connections is None:
            return frame
        
        for start_idx, end_idx in connections:
            if start_idx >= len(landmarks) or end_idx >= len(landmarks):
                continue
            
            x1, y1 = landmarks[start_idx]
            x2, y2 = landmarks[end_idx]
            
            # Denormalize if needed
            if x1 <= 1.0 and y1 <= 1.0:
                px1 = int(x1 * self.frame_width)
                py1 = int(y1 * self.frame_height)
            else:
                px1 = int(x1)
                py1 = int(y1)
            
            if x2 <= 1.0 and y2 <= 1.0:
                px2 = int(x2 * self.frame_width)
                py2 = int(y2 * self.frame_height)
            else:
                px2 = int(x2)
                py2 = int(y2)
            
            # Clamp to frame bounds
            px1 = max(0, min(self.frame_width, px1))
            py1 = max(0, min(self.frame_height, py1))
            px2 = max(0, min(self.frame_width, px2))
            py2 = max(0, min(self.frame_height, py2))
            
            # Draw connection line
            cv2.line(frame, (px1, py1), (px2, py2), color, thickness)
        
        return frame
    
    def draw_debug_info(self, frame, info_dict, position="bottom-left", bg_alpha=0.7):
        """
        Draw debug information on the frame.
        
        Args:
            frame: Input frame (modified in-place)
            info_dict: Dictionary of {key: value} pairs to display
            position: Display position - "bottom-left", "bottom-right", "top-left", "top-right"
            bg_alpha: Background transparency (0.0 to 1.0)
        
        Returns:
            Modified frame
        """
        if not info_dict:
            return frame
        
        font_scale = 0.4
        line_height = 18
        padding = 5
        max_width = 0
        
        # Calculate text dimensions
        text_lines = []
        for key, value in info_dict.items():
            text = f"{key}: {value}"
            text_lines.append(text)
            text_size = cv2.getTextSize(text, self.font_face, font_scale, 1)[0]
            max_width = max(max_width, text_size[0])
        
        # Calculate box position and size
        box_height = len(text_lines) * line_height + 2 * padding
        box_width = max_width + 2 * padding
        
        if "bottom" in position:
            y_start = self.frame_height - box_height - 10
        else:
            y_start = 10
        
        if "right" in position:
            x_start = self.frame_width - box_width - 10
        else:
            x_start = 10
        
        # Draw semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x_start, y_start),
                     (x_start + box_width, y_start + box_height),
                     COLOR_BLACK, -1)
        cv2.addWeighted(overlay, bg_alpha, frame, 1 - bg_alpha, 0, frame)
        
        # Draw border
        cv2.rectangle(frame, (x_start, y_start),
                     (x_start + box_width, y_start + box_height),
                     COLOR_WHITE, 1)
        
        # Draw text
        for i, text in enumerate(text_lines):
            y = y_start + padding + (i + 1) * line_height
            cv2.putText(frame, text, (x_start + padding, y),
                       self.font_face, font_scale, COLOR_CYAN, 1)
        
        return frame


    def overlay_sprite(self, frame, sprite_image, position, alpha=1.0, scale=1.0):
        """
        Overlay a sprite image with alpha blending optimization.
        
        Supports BGRA sprites (with alpha channel) for transparent overlays.
        Uses NumPy-optimized blending for performance.
        
        Args:
            frame: Target frame to draw on (modified in-place) - BGR format
            sprite_image: Sprite image (BGRA format with alpha channel)
            position: Tuple (x, y) for sprite center position
            alpha: Overall opacity multiplier (0.0 to 1.0)
            scale: Scale factor for sprite (1.0=original, 0.5=half, 2.0=double)
        
        Returns:
            Modified frame
        """
        if sprite_image is None or sprite_image.size == 0:
            return frame
        
        # Ensure sprite has alpha channel (BGRA)
        if len(sprite_image.shape) == 2:
            # Grayscale - convert to BGRA
            sprite_bgra = cv2.cvtColor(sprite_image, cv2.COLOR_GRAY2BGRA)
        elif sprite_image.shape[2] == 3:
            # BGR without alpha - add alpha channel (fully opaque)
            sprite_bgra = cv2.cvtColor(sprite_image, cv2.COLOR_BGR2BGRA)
        else:
            sprite_bgra = sprite_image.copy()
        
        # Scale sprite if needed
        if scale != 1.0:
            new_h = int(sprite_bgra.shape[0] * scale)
            new_w = int(sprite_bgra.shape[1] * scale)
            sprite_bgra = cv2.resize(sprite_bgra, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Apply NumPy-optimized alpha blending
        self._blend_sprite_optimized(frame, sprite_bgra, position, alpha)
        
        return frame
    
    def _blend_sprite_optimized(self, frame, sprite_bgra, center, alpha_multiplier):
        """
        NumPy-optimized alpha blending for sprites.
        
        Uses vectorized NumPy operations for fast blending instead of per-pixel loops.
        
        Args:
            frame: Target frame (BGR, modified in-place)
            sprite_bgra: Sprite with alpha channel (BGRA)
            center: Tuple (x, y) for sprite center
            alpha_multiplier: Overall alpha (0.0 to 1.0)
        """
        x, y = int(center[0]), int(center[1])
        sprite_h, sprite_w = sprite_bgra.shape[:2]
        
        # Calculate positioning (center-aligned)
        x1 = x - sprite_w // 2
        y1 = y - sprite_h // 2
        x2 = x1 + sprite_w
        y2 = y1 + sprite_h
        
        # Frame dimensions
        frame_h, frame_w = frame.shape[:2]
        
        # Calculate boundaries (handle off-screen sprites)
        src_x1 = max(0, -x1)
        src_y1 = max(0, -y1)
        src_x2 = sprite_w - max(0, x2 - frame_w)
        src_y2 = sprite_h - max(0, y2 - frame_h)
        
        dst_x1 = max(0, x1)
        dst_y1 = max(0, y1)
        dst_x2 = min(frame_w, x2)
        dst_y2 = min(frame_h, y2)
        
        # Skip if sprite is completely off-screen
        if dst_x1 >= dst_x2 or dst_y1 >= dst_y2 or src_x1 >= src_x2 or src_y1 >= src_y2:
            return
        
        # Extract regions using NumPy slicing
        sprite_region = sprite_bgra[src_y1:src_y2, src_x1:src_x2]
        sprite_rgb = sprite_region[:, :, :3].astype(np.float32)  # BGR channels
        sprite_alpha = sprite_region[:, :, 3].astype(np.float32) / 255.0  # Alpha channel [0,1]
        
        frame_region = frame[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
        
        # Calculate combined alpha: sprite_alpha * alpha_multiplier
        # Expand dimensions for broadcasting
        blend_alpha = sprite_alpha[:, :, np.newaxis] * alpha_multiplier  # Shape: (H, W, 1)
        
        # NumPy-optimized blending: sprite * alpha + frame * (1 - alpha)
        blended = sprite_rgb * blend_alpha + frame_region * (1 - blend_alpha)
        
        # Convert back to uint8 and update frame
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = np.uint8(blended)
    
    def overlay_sprite_animation(self, frame, sprite_frames, position, frame_index,
                                alpha=1.0, scale=1.0):
        """
        Overlay animated sprite from frame list.
        
        Args:
            frame: Target frame to draw on (modified in-place)
            sprite_frames: List of sprite images (BGRA format)
            position: Tuple (x, y) for sprite center
            frame_index: Current animation frame index
            alpha: Overall opacity (0.0 to 1.0)
            scale: Scale factor for sprites
        
        Returns:
            Modified frame
        """
        if not sprite_frames or frame_index < 0:
            return frame
        
        # Wrap frame_index to valid range
        current_index = frame_index % len(sprite_frames)
        current_sprite = sprite_frames[current_index]
        
        return self.overlay_sprite(frame, current_sprite, position, alpha, scale)


# =============================================================================
# Helper Functions
# =============================================================================

def extract_sprite_sheet(image_path, rows, cols):
    """
    Extract individual sprite frames from a sprite sheet.
    
    Reads a PNG sprite sheet and divides it into individual frames by rows and columns.
    Preserves alpha channel (transparency) for each frame.
    
    Args:
        image_path: Path to sprite sheet PNG file
        rows: Number of rows in sprite sheet
        cols: Number of columns in sprite sheet
    
    Returns:
        List of sprite frames (BGRA numpy arrays) or None if load fails
    
    Example:
        sprites = extract_sprite_sheet('fireball_sheet.png', 4, 4)  # 4x4 grid = 16 frames
    """
    from pathlib import Path
    
    image_path = Path(image_path)
    
    if not image_path.exists():
        print(f"⚠ Sprite sheet not found: {image_path}")
        return None
    
    try:
        # Read with IMREAD_UNCHANGED to preserve alpha channel
        image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
        
        if image is None:
            print(f"✗ Failed to load sprite sheet: {image_path}")
            return None
        
        # Handle different image formats
        if len(image.shape) == 2:
            # Grayscale - convert to BGRA
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
        elif image.shape[2] == 3:
            # BGR without alpha - add alpha channel
            image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        elif image.shape[2] == 4:
            # Already BGRA
            pass
        else:
            print(f"✗ Unexpected image format: {image.shape}")
            return None
        
        height, width = image.shape[:2]
        frame_height = height // rows
        frame_width = width // cols
        
        sprites = []
        
        # Extract sprites using NumPy slicing (efficient)
        for row in range(rows):
            for col in range(cols):
                y_start = row * frame_height
                y_end = y_start + frame_height
                x_start = col * frame_width
                x_end = x_start + frame_width
                
                sprite_frame = image[y_start:y_end, x_start:x_end].copy()
                sprites.append(sprite_frame)
        
        print(f"✓ Extracted {len(sprites)} sprites from {image_path.name} ({rows}×{cols} grid)")
        return sprites
    
    except Exception as e:
        print(f"✗ Error extracting sprites: {e}")
        return None


def overlay_sprite_on_landmarks(frame, sprite, landmarks, landmark_indices=None,
                               alpha=0.8, scale=0.5):
    """
    Overlay sprite on multiple hand landmarks.
    
    Useful for placing effect sprites at detected hand keypoints.
    
    Args:
        frame: Target frame (modified in-place)
        sprite: Sprite image (BGRA)
        landmarks: List of (x, y) landmark positions
        landmark_indices: List of landmark indices to overlay on (None=all)
        alpha: Overall opacity
        scale: Scale factor
    
    Returns:
        Modified frame
    """
    if not landmarks or sprite is None:
        return frame
    
    frame_h, frame_w = frame.shape[:2]
    
    # Determine which landmarks to use
    if landmark_indices is None:
        landmark_indices = range(len(landmarks))
    
    renderer = UIRenderer(frame_w, frame_h)
    
    for idx in landmark_indices:
        if 0 <= idx < len(landmarks):
            x, y = landmarks[idx]
            
            # Denormalize if needed
            if x <= 1.0 and y <= 1.0:
                x = int(x * frame_w)
                y = int(y * frame_h)
            else:
                x = int(x)
                y = int(y)
            
            # Clamp to frame
            x = max(0, min(frame_w, x))
            y = max(0, min(frame_h, y))
            
            renderer.overlay_sprite(frame, sprite, (x, y), alpha, scale)
    
    return frame


def calculate_bounding_box(landmarks, frame_width, frame_height, padding=10):
    """
    Calculate bounding box from landmarks.
    
    Args:
        landmarks: List of (x, y) positions (can be normalized or pixel coords)
        frame_width: Frame width for clamping
        frame_height: Frame height for clamping
        padding: Padding around landmarks
    
    Returns:
        Tuple (x1, y1, x2, y2) in pixel coordinates
    """
    if not landmarks or len(landmarks) == 0:
        return (0, 0, frame_width, frame_height)
    
    # Denormalize if needed
    points = []
    for x, y in landmarks:
        if x <= 1.0 and y <= 1.0:
            px = int(x * frame_width)
            py = int(y * frame_height)
        else:
            px = int(x)
            py = int(y)
        points.append((px, py))
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    
    x1 = max(0, min(xs) - padding)
    y1 = max(0, min(ys) - padding)
    x2 = min(frame_width, max(xs) + padding)
    y2 = min(frame_height, max(ys) + padding)
    
    return (x1, y1, x2, y2)


def merge_bounding_boxes(bboxes, frame_width, frame_height, padding=5):
    """
    Merge multiple bounding boxes into one encompassing box.
    
    Args:
        bboxes: List of (x1, y1, x2, y2) tuples
        frame_width: Frame width for clamping
        frame_height: Frame height for clamping
        padding: Padding around merged box
    
    Returns:
        Tuple (x1, y1, x2, y2) of merged bounding box
    """
    if not bboxes:
        return (0, 0, frame_width, frame_height)
    
    x1_min = min(bbox[0] for bbox in bboxes)
    y1_min = min(bbox[1] for bbox in bboxes)
    x2_max = max(bbox[2] for bbox in bboxes)
    y2_max = max(bbox[3] for bbox in bboxes)
    
    x1_min = max(0, x1_min - padding)
    y1_min = max(0, y1_min - padding)
    x2_max = min(frame_width, x2_max + padding)
    y2_max = min(frame_height, y2_max + padding)
    
    return (x1_min, y1_min, x2_max, y2_max)
