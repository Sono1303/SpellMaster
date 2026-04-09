"""
Coordinate Inspector Module - Spell Master Asset Mapping Tool
Interactive tool for identifying sprite/tile coordinates and dimensions.

Features:
    Step 1: Display image and capture mouse coordinates with crosshair
    Step 2: Select rectangular regions and export as JSON format
    
Usage:
    python coordinate_inspector.py [image_file]
    
    Interaction:
    - Click mouse to select coordinates
    - First click: sets start position (top-left)
    - Second click: sets end position (bottom-right) and calculates dimensions
    - Output: JSON format with name and rect [x, y, w, h]
"""

import pygame
import sys
import json
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum


# ============================================================================
# CONFIGURATION & PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
PYGAME_DIR = PROJECT_ROOT / "pygame"
AI_CONTROLLER_DIR = PROJECT_ROOT / "ai_controller"
SCRIPTS_DIR = PYGAME_DIR / "scripts"

sys.path.insert(0, str(AI_CONTROLLER_DIR))

from config import WINDOW_WIDTH, WINDOW_HEIGHT

# Asset directories to search
ASSET_SEARCH_PATHS = [
    PYGAME_DIR / "ingame_assets" / "Texture",
    PYGAME_DIR / "ingame_assets" / "game assets",
    PYGAME_DIR / "ingame_assets" / "map"
]

# Default image
DEFAULT_IMAGE = "TX Tileset Grass.png"

# Image display offset on screen
IMAGE_OFFSET_X = 10
IMAGE_OFFSET_Y = 10

# UI Constants
CROSSHAIR_SIZE = 20
CROSSHAIR_COLOR = (255, 0, 0)  # Red
RECT_COLOR = (0, 255, 0)  # Green
RECT_ALPHA = 100  # Semi-transparent (0-255)
TEXT_COLOR = (255, 255, 255)  # White
TEXT_BG_COLOR = (0, 0, 0)  # Black
UI_FONT_SIZE = 24


# ============================================================================
# COORDINATE STATE MANAGEMENT
# ============================================================================

class SelectionState(Enum):
    """State machine for selection process"""
    WAITING_START = 1      # Waiting for first click
    WAITING_END = 2        # Waiting for second click
    COMPLETE = 3           # Selection complete


class CoordinateSelection:
    """Manages coordinate selection state and validation"""
    
    def __init__(self):
        self.state = SelectionState.WAITING_START
        self.start_pos: Optional[Tuple[int, int]] = None
        self.end_pos: Optional[Tuple[int, int]] = None
        self.selection_name: str = "sprite"
    
    def set_start(self, x: int, y: int):
        """Set the starting position (top-left)"""
        self.start_pos = (x, y)
        self.state = SelectionState.WAITING_END
        print(f"[OK] Start position set: ({x}, {y})")
    
    def set_end(self, x: int, y: int):
        """Set the ending position (bottom-right) and calculate dimensions"""
        self.end_pos = (x, y)
        self.state = SelectionState.COMPLETE
        print(f"[OK] End position set: ({x}, {y})")
        self.print_json_output()
    
    def get_rectangle(self) -> Optional[dict]:
        """Calculate and return rectangle data if both points are set"""
        if self.start_pos is None or self.end_pos is None:
            return None
        
        x_start, y_start = self.start_pos
        x_end, y_end = self.end_pos
        
        # Ensure coordinates are in correct order (top-left to bottom-right)
        x = min(x_start, x_end)
        y = min(y_start, y_end)
        w = abs(x_end - x_start)
        h = abs(y_end - y_start)
        
        return {
            "name": self.selection_name,
            "rect": [x, y, w, h]
        }
    
    def print_json_output(self):
        """Print rectangle data in JSON format to console"""
        rect_data = self.get_rectangle()
        if rect_data:
            json_output = json.dumps(rect_data, indent=2)
            print("\n" + "="*60)
            print(" COPY THIS JSON (image-relative coordinates):")
            print("="*60)
            print(json_output)
            print("="*60)
            print(f"Start: {self.start_pos}, End: {self.end_pos}")
            print("="*60 + "\n")
    
    def reset(self):
        """Reset selection for next region"""
        self.state = SelectionState.WAITING_START
        self.start_pos = None
        self.end_pos = None
        print("\n[*] Selection reset. Ready for next region.\n")


# ============================================================================
# IMAGE LOADING
# ============================================================================

def find_image(filename: str) -> Optional[Path]:
    """
    Search for image file in known asset directories.
    
    Args:
        filename: Name of image file to find
        
    Returns:
        Path to image file if found, None otherwise
    """
    # Check exact path first
    if Path(filename).exists():
        return Path(filename)
    
    # Search in asset directories
    for search_dir in ASSET_SEARCH_PATHS:
        filepath = search_dir / filename
        if filepath.exists():
            return filepath
    
    return None


def load_image(filename: str) -> Optional[pygame.Surface]:
    """
    Load image from file.
    
    Args:
        filename: Name of image file (e.g., 'image_8.png')
        
    Returns:
        pygame.Surface if successful, None otherwise
    """
    filepath = find_image(filename)
    if filepath is None:
        print(f"[X] Image not found: {filename}")
        print(f"  Searched in:")
        for path in ASSET_SEARCH_PATHS:
            print(f"    - {path}")
        return None
    
    try:
        image = pygame.image.load(str(filepath))
        print(f"[OK] Image loaded: {filepath}")
        print(f"  Size: {image.get_width()}x{image.get_height()} pixels")
        return image
    except pygame.error as e:
        print(f"[X] Failed to load image: {e}")
        return None


# ============================================================================
# DRAWING FUNCTIONS
# ============================================================================

def draw_crosshair(surface: pygame.Surface, x: int, y: int, size: int = CROSSHAIR_SIZE, color=CROSSHAIR_COLOR):
    """
    Draw a crosshair at the specified position.
    
    Args:
        surface: pygame.Surface to draw on
        x: X coordinate
        y: Y coordinate
        size: Size of crosshair in pixels
        color: Color in RGB format
    """
    # Horizontal line
    pygame.draw.line(surface, color, (x - size, y), (x + size, y), 2)
    # Vertical line
    pygame.draw.line(surface, color, (x, y - size), (x, y + size), 2)
    # Center dot
    pygame.draw.circle(surface, color, (x, y), 3)


def draw_selection_rect(surface: pygame.Surface, start_pos: Tuple[int, int], end_pos: Tuple[int, int], 
                        color=RECT_COLOR, alpha=RECT_ALPHA):
    """
    Draw a semi-transparent rectangle for selection preview.
    
    Args:
        surface: pygame.Surface to draw on
        start_pos: (x, y) of first corner
        end_pos: (x, y) of second corner
        color: Color in RGB format
        alpha: Transparency (0-255, where 255 is opaque)
    """
    x1, y1 = start_pos
    x2, y2 = end_pos
    
    # Normalize coordinates
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    
    # Draw filled rectangle with transparency
    rect_surface = pygame.Surface((w, h))
    rect_surface.set_colorkey((0, 0, 0))  # Make black transparent
    rect_surface.set_alpha(alpha)
    pygame.draw.rect(rect_surface, color, (0, 0, w, h))
    surface.blit(rect_surface, (x, y))
    
    # Draw outline
    pygame.draw.rect(surface, color, (x, y, w, h), 3)


def draw_info_panel(surface: pygame.Surface, selection: CoordinateSelection, mouse_pos: Tuple[int, int],
                    font: pygame.font.Font):
    """
    Draw information panel with current state and instructions.
    
    Args:
        surface: pygame.Surface to draw on
        selection: CoordinateSelection instance
        mouse_pos: Current mouse position
        font: pygame.font.Font for text
    """
    x, y = mouse_pos
    
    # Prepare text lines
    if selection.state == SelectionState.WAITING_START:
        state_text = "Status: WAITING FOR START POINT"
        instruction_text = "Click to set top-left corner"
    elif selection.state == SelectionState.WAITING_END:
        state_text = "Status: WAITING FOR END POINT"
        instruction_text = "Click to set bottom-right corner"
    else:
        state_text = "Status: COMPLETE"
        instruction_text = "Press R to reset, Q to quit"
    
    # Show image-relative coordinates with indicator
    if 0 <= x < 1000 and 0 <= y < 1000:  # Reasonable bounds check for display
        coord_text = f"Image Coords: ({x}, {y})"
        coord_color = (0, 255, 255)  # Cyan when over image
    else:
        coord_text = f"Outside image"
        coord_color = (255, 100, 100)  # Reddish when outside
    
    # Render text
    state_surf = font.render(state_text, True, TEXT_COLOR, TEXT_BG_COLOR)
    coord_surf = font.render(coord_text, True, coord_color, TEXT_BG_COLOR)
    instr_surf = font.render(instruction_text, True, TEXT_COLOR, TEXT_BG_COLOR)
    
    # Draw with background
    panel_x, panel_y = 10, 10
    padding = 5
    
    surface.blit(state_surf, (panel_x + padding, panel_y + padding))
    surface.blit(coord_surf, (panel_x + padding, panel_y + 35 + padding))
    surface.blit(instr_surf, (panel_x + padding, panel_y + 65 + padding))
    
    # Draw selection info if started
    if selection.start_pos:
        start_text = f"Start: {selection.start_pos}"
        start_surf = font.render(start_text, True, (0, 255, 0), TEXT_BG_COLOR)
        surface.blit(start_surf, (panel_x + padding, panel_y + 100 + padding))
    
    if selection.end_pos:
        rect_data = selection.get_rectangle()
        if rect_data:
            rect_info = f"Rect: {rect_data['rect']}"
            rect_surf = font.render(rect_info, True, (0, 255, 255), TEXT_BG_COLOR)
            surface.blit(rect_surf, (panel_x + padding, panel_y + 130 + padding))


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main(image_filename: str = DEFAULT_IMAGE):
    """
    Main coordinate inspector application.
    
    Args:
        image_filename: Name of image file to inspect
    """
    print("\n" + "="*60)
    print("COORDINATE INSPECTOR - Spell Master Asset Mapping Tool")
    print("="*60)
    print(f"Loading image: {image_filename}\n")
    
    # Initialize Pygame
    pygame.init()
    pygame.mixer.init()
    
    try:
        # Load image
        image = load_image(image_filename)
        if image is None:
            print("[X] Failed to load image. Exiting.")
            pygame.quit()
            return
        
        # Create window
        window_width = max(WINDOW_WIDTH, image.get_width() + 20)
        window_height = max(WINDOW_HEIGHT, image.get_height() + 20)
        screen = pygame.display.set_mode((window_width, window_height))
        pygame.display.set_caption(f"Coordinate Inspector - {image_filename}")
        
        # Setup
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, UI_FONT_SIZE)
        selection = CoordinateSelection()
        mouse_pos = (0, 0)
        
        print("\n" + "="*60)
        print("INSTRUCTIONS:")
        print("="*60)
        print("1. Click to set START point (top-left corner)")
        print("2. Click to set END point (bottom-right corner)")
        print("3. JSON output will be printed to console")
        print("4. Press R to reset selection")
        print("5. Press Q or close window to quit")
        print("="*60 + "\n")
        
        # Main loop
        running = True
        while running:
            clock.tick(60)
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_r:
                        selection.reset()
                
                elif event.type == pygame.MOUSEMOTION:
                    mouse_pos = pygame.mouse.get_pos()
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        screen_x, screen_y = pygame.mouse.get_pos()
                        
                        # Convert screen coordinates to image coordinates
                        img_x = screen_x - IMAGE_OFFSET_X
                        img_y = screen_y - IMAGE_OFFSET_Y
                        
                        # Check if click is within image bounds
                        if 0 <= img_x < image.get_width() and 0 <= img_y < image.get_height():
                            if selection.state == SelectionState.WAITING_START:
                                selection.set_start(img_x, img_y)
                            elif selection.state == SelectionState.WAITING_END:
                                selection.set_end(img_x, img_y)
                            elif selection.state == SelectionState.COMPLETE:
                                # Auto-reset on third click for convenience
                                selection.reset()
                                selection.set_start(img_x, img_y)
                        else:
                            print(f"[!] Click outside image bounds: screen ({screen_x}, {screen_y}) -> image ({img_x}, {img_y})")
            
            # Rendering
            screen.fill((50, 50, 50))  # Dark gray background
            
            # Draw image
            screen.blit(image, (10, 10))
            
            # Convert mouse position to image coordinates for display
            img_mouse_x = mouse_pos[0] - IMAGE_OFFSET_X
            img_mouse_y = mouse_pos[1] - IMAGE_OFFSET_Y
            
            # Draw selection visualization
            if selection.start_pos:
                # Convert image coordinates back to screen for drawing
                screen_start_x = selection.start_pos[0] + IMAGE_OFFSET_X
                screen_start_y = selection.start_pos[1] + IMAGE_OFFSET_Y
                draw_crosshair(screen, screen_start_x, screen_start_y, 
                              size=15, color=(0, 255, 0))  # Green for start
            
            if selection.start_pos and selection.end_pos:
                # Convert image coordinates back to screen for drawing
                screen_start = (selection.start_pos[0] + IMAGE_OFFSET_X, selection.start_pos[1] + IMAGE_OFFSET_Y)
                screen_end = (selection.end_pos[0] + IMAGE_OFFSET_X, selection.end_pos[1] + IMAGE_OFFSET_Y)
                draw_selection_rect(screen, screen_start, screen_end)
            
            # Draw cursor crosshair (only if within image bounds)
            if 0 <= img_mouse_x < image.get_width() and 0 <= img_mouse_y < image.get_height():
                draw_crosshair(screen, mouse_pos[0], mouse_pos[1])
            
            # Draw info panel with image-relative coordinates
            draw_info_panel(screen, selection, (img_mouse_x, img_mouse_y), font)
            
            pygame.display.flip()
        
        print("\n[OK] Inspector closed. Goodbye!\n")
    
    except Exception as e:
        print(f"\n[X] Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        pygame.quit()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Get image filename from command line or use default
    if len(sys.argv) > 1:
        image_file = sys.argv[1]
    else:
        image_file = DEFAULT_IMAGE
    
    main(image_file)
