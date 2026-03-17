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
    {"name": "grass_2", "pos": tile_to_pixel(1, 5)},
    {"name": "grass_2", "pos": tile_to_pixel(1, 6)},
    {"name": "grass_2", "pos": tile_to_pixel(2, 5)},
    {"name": "grass_2", "pos": tile_to_pixel(2, 6)},
    {"name": "grass_2", "pos": tile_to_pixel(10, 1)},
    {"name": "grass_2", "pos": tile_to_pixel(11, 1)},
    {"name": "grass_2", "pos": tile_to_pixel(5, 9)},
    {"name": "grass_2", "pos": tile_to_pixel(6, 9)},
    {"name": "grass_2", "pos": tile_to_pixel(12, 10)},
    {"name": "grass_2", "pos": tile_to_pixel(13, 10)},

    {"name": "medium_thick_wall", "pos": (65, 260)},
    {"name": "medium_thick_wall", "pos": (85, 260)},
    {"name": "medium_thick_wall", "pos": (183, 260)},

    {"name": "medium_thick_wall", "pos": (65, 485)},
    {"name": "medium_thick_wall", "pos": (85, 485)},
    {"name": "medium_thick_wall", "pos": (140, 485)},
    {"name": "medium_thick_wall", "pos": (183, 485)},

    {"name": "wall_up_down", "pos": (65, 260)},
    {"name": "wall_up_down", "pos": (152, 260)},


    {"name": "medium_thick_wall", "pos": (58,705)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(1, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(2, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(3, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(4, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(5, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(6, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(7, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(8, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(9, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(10, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(11, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(12, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(13, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(14, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(15, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(16, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(17, 11)},
    {"name": "medium_thick_wall", "pos": tile_to_pixel(18, 11)},
    {"name": "up_stair", "pos": tile_to_pixel(2, 4)},
    {"name": "stone_stair_1", "pos": (142, 318)},
    {"name": "base", "pos": (127, 253)},
    {"name": "pillar", "pos": (156, 228)},
    {"name": "stone_road_1", "pos": tile_to_pixel(4, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(4, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(4, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(4, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(4, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(5, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(5, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(5, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(5, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(5, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(6, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(6, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(6, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(6, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(6, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(7, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(7, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(7, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(7, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(7, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(8, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(8, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(8, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(8, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(8, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(9, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(9, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(9, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(9, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(9, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(10, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(10, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(10, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(10, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(10, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(11, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(11, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(11, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(11, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(11, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(12, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(12, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(12, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(12, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(12, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(13, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(13, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(13, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(13, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(13, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(14, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(14, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(14, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(14, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(14, 7)},
    {"name": "stone_road_1", "pos": tile_to_pixel(15, 3)},
    {"name": "stone_road_1", "pos": tile_to_pixel(15, 4)},
    {"name": "stone_road_1", "pos": tile_to_pixel(15, 5)},
    {"name": "stone_road_1", "pos": tile_to_pixel(15, 6)},
    {"name": "stone_road_1", "pos": tile_to_pixel(15, 7)},

    {"name": "wall_up_down", "pos": (65, 485)},
    {"name": "wall_up_down", "pos": (153, 485)},

    {"name": "wall_left", "pos": (241, 526)},
    {"name": "wall_left", "pos": (241, 485)},

    {"name": "medium_thick_wall", "pos": (241, 560)},
    {"name": "medium_thick_wall", "pos": (300, 560)},
    {"name": "medium_thick_wall", "pos": (320, 560)},
    {"name": "medium_thick_wall", "pos": (340, 560)},
    {"name": "medium_thick_wall", "pos": (360, 560)},
    {"name": "medium_thick_wall", "pos": (380, 560)},
    {"name": "medium_thick_wall", "pos": (400, 560)},
    {"name": "medium_thick_wall", "pos": (420, 560)},
    {"name": "medium_thick_wall", "pos": (440, 560)},
    {"name": "medium_thick_wall", "pos": (460, 560)},
    {"name": "medium_thick_wall", "pos": (480, 560)},
    {"name": "medium_thick_wall", "pos": (500, 560)},
    {"name": "medium_thick_wall", "pos": (520, 560)},
    {"name": "medium_thick_wall", "pos": (540, 560)},
    {"name": "medium_thick_wall", "pos": (560, 560)},
    {"name": "medium_thick_wall", "pos": (580, 560)},
    {"name": "medium_thick_wall", "pos": (600, 560)},
    {"name": "medium_thick_wall", "pos": (620, 560)},
    {"name": "medium_thick_wall", "pos": (640, 560)},
    {"name": "medium_thick_wall", "pos": (660, 560)},
    {"name": "medium_thick_wall", "pos": (680, 560)},
    {"name": "medium_thick_wall", "pos": (700, 560)},
    {"name": "medium_thick_wall", "pos": (720, 560)},
    {"name": "medium_thick_wall", "pos": (740, 560)},
    {"name": "medium_thick_wall", "pos": (760, 560)},
    {"name": "medium_thick_wall", "pos": (780, 560)},
    {"name": "medium_thick_wall", "pos": (800, 560)},
    {"name": "medium_thick_wall", "pos": (820, 560)},
    {"name": "medium_thick_wall", "pos": (840, 560)},
    {"name": "medium_thick_wall", "pos": (860, 560)},
    {"name": "medium_thick_wall", "pos": (880, 560)},
    {"name": "medium_thick_wall", "pos": (900, 560)},
    {"name": "medium_thick_wall", "pos": (920, 560)},
    {"name": "medium_thick_wall", "pos": (940, 560)},
    {"name": "medium_thick_wall", "pos": (960, 560)},
    {"name": "medium_thick_wall", "pos": (970, 560)},
    
    {"name": "medium_thick_wall", "pos": (241, 125)},
    {"name": "medium_thick_wall", "pos": (300, 125)},
    {"name": "medium_thick_wall", "pos": (320, 125)},
    {"name": "medium_thick_wall", "pos": (340, 125)},
    {"name": "medium_thick_wall", "pos": (360, 125)},
    {"name": "medium_thick_wall", "pos": (380, 125)},
    {"name": "medium_thick_wall", "pos": (400, 125)},
    {"name": "medium_thick_wall", "pos": (420, 125)},
    {"name": "medium_thick_wall", "pos": (440, 125)},
    {"name": "medium_thick_wall", "pos": (460, 125)},
    {"name": "medium_thick_wall", "pos": (480, 125)},
    {"name": "medium_thick_wall", "pos": (500, 125)},
    {"name": "medium_thick_wall", "pos": (520, 125)},
    {"name": "medium_thick_wall", "pos": (540, 125)},
    {"name": "medium_thick_wall", "pos": (560, 125)},
    {"name": "medium_thick_wall", "pos": (580, 125)},
    {"name": "medium_thick_wall", "pos": (600, 125)},
    {"name": "medium_thick_wall", "pos": (620, 125)},
    {"name": "medium_thick_wall", "pos": (640, 125)},
    {"name": "medium_thick_wall", "pos": (660, 125)},
    {"name": "medium_thick_wall", "pos": (680, 125)},
    {"name": "medium_thick_wall", "pos": (700, 125)},
    {"name": "medium_thick_wall", "pos": (720, 125)},
    {"name": "medium_thick_wall", "pos": (740, 125)},
    {"name": "medium_thick_wall", "pos": (760, 125)},
    {"name": "medium_thick_wall", "pos": (780, 125)},
    {"name": "medium_thick_wall", "pos": (800, 125)},
    {"name": "medium_thick_wall", "pos": (820, 125)},
    {"name": "medium_thick_wall", "pos": (840, 125)},
    {"name": "medium_thick_wall", "pos": (860, 125)},
    {"name": "medium_thick_wall", "pos": (880, 125)},
    {"name": "medium_thick_wall", "pos": (900, 125)},
    {"name": "medium_thick_wall", "pos": (920, 125)},
    {"name": "medium_thick_wall", "pos": (940, 125)},
    {"name": "medium_thick_wall", "pos": (960, 125)},
    {"name": "medium_thick_wall", "pos": (970, 125)},

    {"name": "wall_left", "pos": (241, 125)},
    {"name": "wall_left", "pos": (241, 165)},

    {"name": "rock", "pos": tile_to_pixel(3, 10)},
    {"name": "rock", "pos": tile_to_pixel(2, 2)},

    {"name": "energy", "pos": (143, 420)},
    {"name": "energy", "pos": (160, 420)},
    {"name": "energy", "pos": (177, 420)},
    {"name": "energy", "pos": (194, 420)},

    {"name": "energy", "pos": (143, 437)},
    {"name": "energy", "pos": (160, 437)},
    {"name": "energy", "pos": (177, 437)},
    {"name": "energy", "pos": (194, 437)},

    {"name": "trunks", "pos": tile_to_pixel(3, 3)},
    {"name": "trunks", "pos": tile_to_pixel(10, 10)},
    {"name": "trunks", "pos": (428, 85)},

    {"name": "tomb_1", "pos": tile_to_pixel(16, 1)},
    {"name": "tomb_1", "pos": tile_to_pixel(16, 1)},
    {"name": "tomb_2", "pos": tile_to_pixel(17, 10)},


    {"name": "wall_left", "pos": (58, 60)},
    {"name": "wall_left", "pos": (58, 156)},
    {"name": "wall_left", "pos": (58, 252)},
    {"name": "wall_left", "pos": (58, 348)},
    {"name": "wall_left", "pos": (58, 444)},
    {"name": "wall_left", "pos": (58, 540)},
    {"name": "wall_left", "pos": (58, 610)},
    {"name": "wall_up_down", "pos": (63, 699)},
    {"name": "wall_up_down", "pos": (160, 699)},
    {"name": "wall_up_down", "pos": (257, 699)},
    {"name": "wall_up_down", "pos": (354, 699)},
    {"name": "wall_up_down", "pos": (451, 699)},
    {"name": "wall_up_down", "pos": (548, 699)},
    {"name": "wall_up_down", "pos": (645, 699)},
    {"name": "wall_up_down", "pos": (742, 699)},
    {"name": "wall_up_down", "pos": (839, 699)},
    {"name": "wall_up_down", "pos": (936, 699)},
    {"name": "wall_up_down", "pos": (1033, 699)},
    {"name": "wall_up_down", "pos": (1120, 699)},
    {"name": "wall_up_down", "pos": (60, 60)},
    {"name": "wall_up_down", "pos": (157, 60)},
    {"name": "wall_up_down", "pos": (254, 60)},
    {"name": "wall_up_down", "pos": (316, 60)},
    {"name": "wall_up_down", "pos": (413, 60)},
    {"name": "wall_up_down", "pos": (510, 60)},
    {"name": "wall_up_down", "pos": (607, 60)},
    {"name": "wall_up_down", "pos": (704, 60)},
    {"name": "wall_up_down", "pos": (801, 60)},
    {"name": "wall_up_down", "pos": (898, 60)},
    {"name": "wall_up_down", "pos": (995, 60)},
    {"name": "wall_up_down", "pos": (1092, 60)},
    {"name": "wall_up_down", "pos": (1120, 60)},
    {"name": "wall_right", "pos": (1210, 60)},
    {"name": "wall_right", "pos": (1210, 157)},
    {"name": "wall_right", "pos": (1210, 254)},
    {"name": "wall_right", "pos": (1210, 351)},
    {"name": "wall_right", "pos": (1210, 445)},
    {"name": "wall_right", "pos": (1210, 542)},
    {"name": "wall_right", "pos": (1210, 605)},
    {"name": "tree_1", "pos": tile_to_pixel(1, 8)},
    {"name": "tree_1", "pos": tile_to_pixel(1, 2)},

    
    # Add more objects as needed - just update this list!
    # {"name": "tree_1", "pos": tile_to_pixel(15, 2)},
    # {"name": "fence_section", "pos": tile_to_pixel(8, 5)},
]
