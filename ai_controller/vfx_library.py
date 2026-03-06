"""
OpenCV Spell VFX Library
Provides visual effects for spell recognition: Fireball, Ice Shards, Lightning
"""

import cv2
import numpy as np
from pathlib import Path


class VFXEffect:
    """Base class for VFX effects with timer management."""
    
    def __init__(self, duration=30):
        """
        Initialize VFX effect.
        
        Args:
            duration: Number of frames the effect lasts
        """
        self.duration = duration
        self.remaining_duration = duration
        self.is_active = False
    
    def trigger(self):
        """Activate the effect."""
        self.remaining_duration = self.duration
        self.is_active = True
    
    def update(self):
        """Update effect timer. Returns True if effect is still active."""
        if self.is_active:
            self.remaining_duration -= 1
            if self.remaining_duration <= 0:
                self.is_active = False
                return False
        return self.is_active
    
    def get_alpha(self):
        """Get fade-out alpha value (0-1) based on remaining duration."""
        if self.duration <= 0:
            return 0
        alpha = self.remaining_duration / self.duration
        return max(0, min(1, alpha))


class FireballEffect(VFXEffect):
    """Fireball effect with concentric colored circles and glow."""
    
    def __init__(self, duration=30):
        super().__init__(duration)
        self.max_radius = 150
    
    def draw(self, frame, center):
        """
        Draw fireball effect on frame.
        
        Args:
            frame: OpenCV frame/image
            center: Tuple (x, y) for effect center
        """
        if not self.is_active:
            return
        
        alpha = self.get_alpha()
        x, y = int(center[0]), int(center[1])
        
        # Create temporary overlay for glow effect
        overlay = frame.copy()
        
        # Draw concentric circles: Red -> Orange -> Yellow
        colors = [
            (0, 0, 255),      # Red
            (0, 165, 255),    # Orange
            (0, 255, 255)     # Yellow
        ]
        
        radius_step = self.max_radius // len(colors)
        
        for i, color in enumerate(colors):
            radius = int((i + 1) * radius_step * alpha)
            if radius > 0:
                cv2.circle(overlay, (x, y), radius, color, -1)
        
        # Apply Gaussian blur for glow effect
        kernel_size = int(31 * alpha)
        if kernel_size % 2 == 0:
            kernel_size += 1
        if kernel_size > 1:
            overlay = cv2.GaussianBlur(overlay, (kernel_size, kernel_size), 0)
        
        # Blend overlay with original frame
        fade_alpha = alpha * 0.6  # Adjust opacity
        frame[:] = cv2.addWeighted(overlay, fade_alpha, frame, 1 - fade_alpha, 0)


class IceEffect(VFXEffect):
    """Ice Shards effect with cyan overlay and diamond shapes."""
    
    def __init__(self, duration=30):
        super().__init__(duration)
        self.max_radius = 150
        self.num_shards = 12
        np.random.seed(42)  # For reproducible shard positions
    
    def draw(self, frame, center):
        """
        Draw ice shards effect on frame.
        
        Args:
            frame: OpenCV frame/image
            center: Tuple (x, y) for effect center
        """
        if not self.is_active:
            return
        
        alpha = self.get_alpha()
        x, y = int(center[0]), int(center[1])
        
        # Create overlay for cyan base
        overlay = frame.copy()
        
        # Draw cyan overlay box
        box_size = int(self.max_radius * 2 * alpha)
        cv2.rectangle(
            overlay,
            (max(0, x - box_size), max(0, y - box_size)),
            (min(frame.shape[1], x + box_size), min(frame.shape[0], y + box_size)),
            (255, 255, 0),  # Cyan
            -1
        )
        
        # Blend cyan overlay
        cyan_alpha = alpha * 0.3
        frame_temp = cv2.addWeighted(overlay, cyan_alpha, frame, 1 - cyan_alpha, 0)
        
        # Draw ice shards (diamond shapes)
        shard_size = int(20 * alpha)
        
        for i in range(self.num_shards):
            # Random angle and distance
            angle = (i / self.num_shards) * 2 * np.pi + np.random.uniform(-0.3, 0.3)
            distance = np.random.uniform(self.max_radius * 0.3, self.max_radius * alpha)
            
            shard_x = int(x + distance * np.cos(angle))
            shard_y = int(y + distance * np.sin(angle))
            
            # Draw diamond (rotated square)
            points = np.array([
                [shard_x, shard_y - shard_size],
                [shard_x + shard_size, shard_y],
                [shard_x, shard_y + shard_size],
                [shard_x - shard_size, shard_y]
            ], np.int32)
            
            cv2.polylines(frame_temp, [points], True, (255, 255, 255), 2)
            cv2.fillPoly(frame_temp, [points], (200, 255, 255), cv2.LINE_AA)
        
        frame[:] = frame_temp


class LightningEffect(VFXEffect):
    """Lightning/Chidori effect with zigzag lines."""
    
    def __init__(self, duration=30):
        super().__init__(duration)
        self.max_radius = 200
        self.num_bolts = 8
        np.random.seed(42)
    
    def draw(self, frame, center):
        """
        Draw lightning effect on frame.
        
        Args:
            frame: OpenCV frame/image
            center: Tuple (x, y) for effect center
        """
        if not self.is_active:
            return
        
        alpha = self.get_alpha()
        x, y = int(center[0]), int(center[1])
        
        # Draw multiple lightning bolts radiating from center
        for bolt_idx in range(self.num_bolts):
            # Base angle for this bolt
            angle = (bolt_idx / self.num_bolts) * 2 * np.pi
            
            # Create zigzag path
            points = [(x, y)]
            current_x, current_y = x, y
            
            num_segments = int(10 * alpha)
            segment_length = int(self.max_radius / max(1, num_segments))
            
            for segment in range(num_segments):
                # Add zigzag pattern
                offset = np.random.uniform(-15, 15) * alpha
                next_x = int(x + (segment + 1) * segment_length * np.cos(angle + offset / 100))
                next_y = int(y + (segment + 1) * segment_length * np.sin(angle + offset / 100))
                
                points.append((next_x, next_y))
            
            # Draw the lightning bolt
            for i in range(len(points) - 1):
                start_pt = points[i]
                end_pt = points[i + 1]
                
                # Draw white core
                cv2.line(frame, start_pt, end_pt, (255, 255, 255), 2)
                
                # Draw cyan outer glow
                cv2.line(frame, start_pt, end_pt, (255, 255, 0), 5)
        
        # Add bloom effect with Gaussian blur
        if alpha > 0.3:
            glow_copy = frame.copy()
            kernel_size = int(21 * alpha)
            if kernel_size % 2 == 0:
                kernel_size += 1
            if kernel_size > 1:
                glow_copy = cv2.GaussianBlur(glow_copy, (kernel_size, kernel_size), 0)
                frame[:] = cv2.addWeighted(frame, 0.8, glow_copy, 0.2, 0)


class VFXManager:
    """Manages all VFX effects with timer system."""
    
    def __init__(self):
        """Initialize VFX manager with all available effects."""
        self.effects = {
            'Tiger': FireballEffect(duration=30),
            'Fireball': FireballEffect(duration=30),
            'Dragon': IceEffect(duration=30),
            'Ice': IceEffect(duration=30),
            'Ox': LightningEffect(duration=30),
            'Lightning': LightningEffect(duration=30),
        }
        
        self.current_effect_type = None
        self.effect_center = None
    
    def trigger_spell(self, spell_label):
        """
        Trigger a spell effect.
        
        Args:
            spell_label: Name of the spell (e.g., 'Tiger', 'Dragon', 'Ox')
        """
        if spell_label in self.effects:
            self.effects[spell_label].trigger()
            self.current_effect_type = spell_label
    
    def update_and_draw(self, frame, center_position):
        """
        Update all active effects and draw them on frame.
        
        Args:
            frame: OpenCV frame/image
            center_position: Tuple (x, y) for effect center
        """
        self.effect_center = center_position
        
        # Update all effects
        for spell_label, effect in self.effects.items():
            if effect.is_active:
                effect.update()
                effect.draw(frame, center_position)
    
    def is_any_active(self):
        """Check if any effect is currently active."""
        return any(effect.is_active for effect in self.effects.values())
    
    def get_active_spells(self):
        """Get list of currently active spell names."""
        return [label for label, effect in self.effects.items() if effect.is_active]


def overlay_png(frame, png_image, position, alpha=0.7):
    """
    Overlay a PNG image with transparency on frame.
    
    Args:
        frame: OpenCV frame/image (BGR)
        png_image: OpenCV image with alpha channel (BGRA) or BGR
        position: Tuple (x, y) for top-left corner of overlay
        alpha: Opacity of overlay (0-1)
    
    Returns:
        Modified frame with overlaid image
    """
    x, y = int(position[0]), int(position[1])
    
    # Handle case with alpha channel
    if png_image.shape[2] == 4:
        # Extract alpha channel
        png_alpha = png_image[:, :, 3] / 255.0
        png_bgr = png_image[:, :, :3]
    else:
        png_bgr = png_image
        png_alpha = np.ones((png_image.shape[0], png_image.shape[1]))
    
    h, w = png_bgr.shape[:2]
    
    # Calculate boundaries
    y1 = max(0, y)
    y2 = min(frame.shape[0], y + h)
    x1 = max(0, x)
    x2 = min(frame.shape[1], x + w)
    
    # Calculate corresponding region in png image
    py1 = max(0, -y)
    py2 = py1 + (y2 - y1)
    px1 = max(0, -x)
    px2 = px1 + (x2 - x1)
    
    # Blend using alpha
    for c in range(3):
        frame[y1:y2, x1:x2, c] = (
            png_bgr[py1:py2, px1:px2, c] * png_alpha[py1:py2, px1:px2] * alpha +
            frame[y1:y2, x1:x2, c] * (1 - png_alpha[py1:py2, px1:px2] * alpha)
        ).astype(np.uint8)
    
    return frame


def draw_vfx(frame, effect_type, center_coord, vfx_manager):
    """
    Main function to draw VFX effect on frame.
    
    Args:
        frame: OpenCV frame/image
        effect_type: Type of effect ('Tiger', 'Dragon', 'Ox', etc.)
        center_coord: Tuple (x, y) for effect center
        vfx_manager: VFXManager instance
    """
    vfx_manager.trigger_spell(effect_type)
    vfx_manager.update_and_draw(frame, center_coord)


if __name__ == "__main__":
    # Test the VFX library
    print("VFX Library loaded successfully")
    print("Available effects: Fireball (Tiger), Ice (Dragon), Lightning (Ox)")
