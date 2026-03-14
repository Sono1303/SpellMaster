"""
Map Data Module - Spell Master Game World Blueprints
Defines tile-based map layouts for each game level using a simple integer encoding system.

Tile Types:
    -1 = Black (void/nền đen) - empty/non-playable area
    0 = Grass (walkable terrain) - default ground
    1 = Path (pathway/road) - primary walkway
    2 = Shrine (shrine/altar placement) - sacred location for tower placement

Map Structure:
    Each map is a 2D list (list of lists) where:
    - Row = vertical position (Y-axis)
    - Column = horizontal position (X-axis)
    - Each cell is a single integer representing the tile type
"""

# ============================================================================
# LEVEL 1 - Base Level (Introduction)
# ============================================================================
"""
Map size: 20 columns × 8 rows
Features: Winding path from entrance (top-left) leading to shrine at center
Design: Single path creates strategic depth for tower placement
"""

LEVEL_1_BASE = [
    # Row 0
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
    # Row 1
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 2
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 3
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 4
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 5
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 6
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 7
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 8 - Center row with Shrine
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 9
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 10
    [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1],
    # Row 11
    [-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1],
]

# Map metadata
MAP_DIMENSIONS = {
    "width": 20,  # columns
    "height": 8,   # rows (updated from 15 to 8)
    "tile_size": 64,  # pixels per tile (1280/20)
}

def tile_to_pixel(tile_x: int, tile_y: int, tile_size: int = 64) -> tuple:
    """
    Convert tile coordinates to pixel coordinates.
    
    Tile (0, 0) = top-left corner of tile (0, 0)
    
    Args:
        tile_x: Tile column (0-based)
        tile_y: Tile row (0-based)
        tile_size: Pixel size of one tile (default 64)
    
    Returns:
        Tuple (pixel_x, pixel_y)
    
    Example:
        >>> tile_to_pixel(1, 2, 64)
        (64, 128)
    """
    return (tile_x * tile_size, tile_y * tile_size)

# ============================================================================
# DECORATIONS/OBJECTS LAYER
# ============================================================================
"""
Objects placed on top of the tile layer. Each object has:
- name: Asset name (from sprite sheet JSON)
- pos: (pixel_x, pixel_y) position on screen
  
Easy positioning:
- Using tile_to_pixel(): tile_to_pixel(col, row) converts tile coords to pixels
- Using pixel: (x, y) for direct pixel control

Example:
    {"name": "stone_stair_1", "pos": tile_to_pixel(3, 2)}
    {"name": "tree_1", "pos": (100, 150)}
"""

LEVEL_1_OBJECTS = [
    {"name": "stone_stair_1", "pos": (63, 63)},
    {"name": "wall_left", "pos": (58, 60)},
    {"name": "wall_left", "pos": (58, 156)},
    {"name": "wall_left", "pos": (58, 252)},
    {"name": "wall_left", "pos": (58, 348)},
    {"name": "wall_left", "pos": (58, 444)},
    {"name": "wall_left", "pos": (58, 540)},
    {"name": "wall_left", "pos": (58, 610)},
    {"name": "wall_right", "pos": tile_to_pixel(17, 6)},
    
    # Add more objects as needed - just update this list!
    # {"name": "tree_1", "pos": tile_to_pixel(15, 2)},
    # {"name": "fence_section", "pos": tile_to_pixel(8, 5)},
]
