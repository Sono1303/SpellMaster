"""
Map Engine Module - Spell Master Tile System
Handles tile-based map rendering, tile asset management, and map display logic.

Classes:
    TileManager: Manages tile image loading and caching
    TileMap: Renders 2D tile-based maps to screen
"""

import pygame
from pathlib import Path
from typing import List, Optional, Tuple


class TileManager:
    """
    Manages loading, caching, and retrieving tile images.
    
    Tile images are loaded once and cached in memory to optimize rendering performance.
    Each tile image is assumed to be a square (tile_size × tile_size pixels).
    Supports searching multiple asset directories for flexibility.
    """
    
    def __init__(self, asset_dir: Path, tile_size: int = 64, search_paths: Optional[list] = None):
        """
        Initialize the TileManager.
        
        Args:
            asset_dir: Primary path to directory containing tile images
            tile_size: Size of tile in pixels (default: 64×64)
            search_paths: Optional list of additional paths to search for tiles
        """
        self.asset_dir = Path(asset_dir)
        self.tile_size = tile_size
        self.tile_cache = {}  # Cache for loaded tile images
        self.search_paths = [self.asset_dir]
        if search_paths:
            self.search_paths.extend([Path(p) for p in search_paths])
        
    def load_tile(self, filename: str) -> pygame.Surface:
        """
        Load a tile image from file. Returns cached version if already loaded.
        Searches through multiple asset directories if tile not found in primary path.
        
        Args:
            filename: Name of the image file (e.g., 'image_8.png')
            
        Returns:
            pygame.Surface: Scaled tile image (tile_size × tile_size)
            
        Raises:
            FileNotFoundError: If image file not found in any search path
            pygame.error: If image cannot be loaded
        """
        if filename in self.tile_cache:
            return self.tile_cache[filename]
        
        # Try to find the file in search paths
        filepath = None
        for search_dir in self.search_paths:
            candidate = search_dir / filename
            if candidate.exists():
                filepath = candidate
                break
        
        if filepath is None:
            raise FileNotFoundError(
                f"Tile image not found: {filename}\n"
                f"  Searched in: {', '.join(str(p) for p in self.search_paths)}"
            )
        
        try:
            image = pygame.image.load(str(filepath))
            # Scale to tile size
            image = pygame.transform.scale(image, (self.tile_size, self.tile_size))
            self.tile_cache[filename] = image
            return image
        except pygame.error as e:
            raise pygame.error(f"Failed to load tile image {filename}: {e}")
    
    def get_tile(self, filename: str) -> pygame.Surface:
        """
        Get a tile image (from cache or load if not cached).
        
        Args:
            filename: Name of the image file
            
        Returns:
            pygame.Surface: The tile image
        """
        return self.load_tile(filename)
    
    def clear_cache(self):
        """Clear the tile cache to free memory."""
        self.tile_cache.clear()


class TileMap:
    """
    Renders a 2D tile-based map to a pygame surface.
    
    The map is represented as a 2D list of integers (tile IDs), and this class
    handles the conversion of tile IDs to visual tiles and rendering them to screen.
    """
    
    def __init__(
        self,
        map_data: List[List[int]],
        tile_manager: TileManager,
        tile_id_to_file: dict,
        map_width: int = None,
        map_height: int = None,
        tile_size: int = 64,
        resource_manager=None
    ):
        """
        Initialize the TileMap.
        
        Map dimensions are automatically calculated from the actual map data.
        The map_width and map_height parameters are OPTIONAL and will be
        overridden by the actual data dimensions.
        
        Args:
            map_data: 2D list of tile IDs (integers)
            tile_manager: TileManager instance for loading tiles
            tile_id_to_file: Dict mapping tile ID to filename OR asset name
                If resource_manager is provided, these are interpreted as asset names
                Otherwise, they're interpreted as filenames
            map_width: [DEPRECATED] Ignored - calculated from len(map_data[0])
            map_height: [DEPRECATED] Ignored - calculated from len(map_data)
            tile_size: Size of each tile in pixels
            resource_manager: Optional ResourceManager for loading sprites by asset name
        """
        self.map_data = map_data
        self.tile_manager = tile_manager
        self.tile_id_to_file = tile_id_to_file
        self.resource_manager = resource_manager
        
        # Calculate dimensions from actual map data (DYNAMIC)
        self.map_height = len(map_data) if map_data else 0
        self.map_width = len(map_data[0]) if map_data and len(map_data) > 0 else 0
        self.tile_size = tile_size
        
        # Calculate pixel dimensions from actual map dimensions
        self.pixel_width = self.map_width * self.tile_size
        self.pixel_height = self.map_height * self.tile_size
        
        # Pre-load all tile images
        self.tiles = {}
        self._load_all_tiles()
    
    def _load_all_tiles(self):
        """Pre-load all tile images used in the map. Skip -1 (black void)."""
        unique_tile_ids = set()
        for row in self.map_data:
            for tile_id in row:
                unique_tile_ids.add(tile_id)
        
        for tile_id in unique_tile_ids:
            if tile_id == -1:
                # Skip black void - will be drawn as solid color
                continue
            
            if tile_id in self.tile_id_to_file:
                asset_or_filename = self.tile_id_to_file[tile_id]
                
                try:
                    # If resource_manager is available, load by asset name
                    if self.resource_manager:
                        sprite = self.resource_manager.get_asset(asset_or_filename)
                        if sprite is not None:
                            # Scale sprite to tile size if needed
                            if sprite.get_width() != self.tile_size or sprite.get_height() != self.tile_size:
                                sprite = pygame.transform.scale(sprite, (self.tile_size, self.tile_size))
                            self.tiles[tile_id] = sprite
                        else:
                            print(f"Warning: Asset '{asset_or_filename}' not found for tile {tile_id}")
                    else:
                        # Fallback to load by filename using tile_manager
                        self.tiles[tile_id] = self.tile_manager.get_tile(asset_or_filename)
                except Exception as e:
                    print(f"Warning: Could not load tile {tile_id} ({asset_or_filename}): {e}")
    
    def render(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0):
        """
        Render the entire tilemap to a pygame surface.
        
        Tiles are rendered in order:
        - If tile image loaded: blit image
        - If tile_id == -1 (black void): draw black rectangle
        - Otherwise: skip (transparent)
        
        Args:
            surface: pygame.Surface to render onto (typically the screen)
            offset_x: X pixel offset for rendering (for camera/scrolling)
            offset_y: Y pixel offset for rendering (for camera/scrolling)
        """
        for row_idx, row in enumerate(self.map_data):
            for col_idx, tile_id in enumerate(row):
                # Calculate screen position
                screen_x = col_idx * self.tile_size + offset_x
                screen_y = row_idx * self.tile_size + offset_y
                
                if tile_id == -1:
                    # Black void - draw solid black rectangle
                    pygame.draw.rect(surface, (0, 0, 0), 
                                   (screen_x, screen_y, self.tile_size, self.tile_size))
                elif tile_id in self.tiles:
                    # Draw tile image
                    surface.blit(self.tiles[tile_id], (screen_x, screen_y))
    
    def get_tile_at(self, col: int, row: int) -> Optional[int]:
        """
        Get tile ID at specific grid coordinates.
        
        Args:
            col: Column index (0 to map_width-1)
            row: Row index (0 to map_height-1)
            
        Returns:
            Tile ID or None if out of bounds
        """
        if 0 <= row < self.map_height and 0 <= col < self.map_width:
            return self.map_data[row][col]
        return None
    
    def is_walkable(self, col: int, row: int, walkable_tiles: List[int]) -> bool:
        """
        Check if a tile at given coordinates is walkable.
        
        Args:
            col: Column index
            row: Row index
            walkable_tiles: List of tile IDs that are considered walkable
            
        Returns:
            True if tile is walkable, False otherwise
        """
        tile_id = self.get_tile_at(col, row)
        return tile_id in walkable_tiles if tile_id is not None else False
    
    def is_walkable_pixel(self, pixel_x: float, pixel_y: float, collision_box_size: int = 20, debug: bool = False) -> bool:
        """
        Check if position at given pixel coordinates is walkable.
        
        Converts pixel coordinates to tile coordinates and checks if that tile
        allows walking. Uses walkable_tiles list from tile_configuration.
        
        Args:
            pixel_x: X position in pixels
            pixel_y: Y position in pixels
            collision_box_size: Size of collision box for entity (used for multi-point check)
                                Checks center point and 4 corners
            debug: If True, print detailed collision info
            
        Returns:
            True if position is walkable, False if blocked by obstacle
        """
        # Convert pixel coordinates to tile coordinates
        center_col = int(pixel_x / self.tile_size)
        center_row = int(pixel_y / self.tile_size)
        
        # Check center point
        center_tile = self.get_tile_at(center_col, center_row)
        is_center_walkable = self._is_tile_walkable(center_tile)
        
        if debug:
            tile_name = self._get_tile_name(center_tile)
            print(f"  Center ({pixel_x:.0f}, {pixel_y:.0f}) -> Tile ({center_col}, {center_row}): "
                  f"ID={center_tile}, Name='{tile_name}', Walkable={is_center_walkable}")
        
        if not is_center_walkable:
            return False
        
        # Check 4 corners of collision box for more accurate collision
        # This prevents player from squeezing through tight spaces or clipping into objects
        corners = [
            (pixel_x, pixel_y),  # Top-left
            (pixel_x + collision_box_size, pixel_y),  # Top-right
            (pixel_x, pixel_y + collision_box_size),  # Bottom-left
            (pixel_x + collision_box_size, pixel_y + collision_box_size),  # Bottom-right
        ]
        
        for i, (corner_x, corner_y) in enumerate(corners):
            corner_col = int(corner_x / self.tile_size)
            corner_row = int(corner_y / self.tile_size)
            corner_tile = self.get_tile_at(corner_col, corner_row)
            is_corner_walkable = self._is_tile_walkable(corner_tile)
            
            if debug:
                tile_name = self._get_tile_name(corner_tile)
                corner_names = ["TL", "TR", "BL", "BR"]
                print(f"    Corner {corner_names[i]} ({corner_x:.0f}, {corner_y:.0f}) -> "
                      f"Tile ({corner_col}, {corner_row}): ID={corner_tile}, Name='{tile_name}', Walkable={is_corner_walkable}")
            
            if not is_corner_walkable:
                return False
        
        return True
    
    def is_walkable_with_decorations(self, pixel_x: float, pixel_y: float, 
                                     decorations: list = None, 
                                     collision_box_size: int = 20, 
                                     debug: bool = False) -> tuple:
        """
        Check if position is walkable, including collision with decoration objects.
        
        Args:
            pixel_x: X position in pixels
            pixel_y: Y position in pixels
            decorations: List of decoration objects with collision info
            collision_box_size: Size of collision box
            debug: If True, print debug info including decoration collision
            
        Returns:
            Tuple (is_walkable: bool, collision_object_name: str or None)
                - is_walkable: False if blocked by tile or decoration
                - collision_object_name: Name of colliding decoration, or None
        """
        # First check tile walkability
        tile_walkable = self.is_walkable_pixel(pixel_x, pixel_y, collision_box_size, debug=debug)
        if not tile_walkable:
            return (False, None)
        
        # Then check decoration collisions
        if decorations:
            # Create collision box
            collision_box = pygame.Rect(pixel_x, pixel_y, collision_box_size, collision_box_size)
            
            for decoration in decorations:
                # Check if decoration has collision enabled
                if not decoration.get('collision', True):  # Default: collision enabled
                    continue
                
                # Get decoration position and size
                deco_pos = decoration.get('pos', (0, 0))
                deco_width = decoration.get('width', 64)  # Default tile size
                deco_height = decoration.get('height', 64)
                
                # Create decoration collision box
                deco_box = pygame.Rect(deco_pos[0], deco_pos[1], deco_width, deco_height)
                
                # Check collision
                if collision_box.colliderect(deco_box):
                    deco_name = decoration.get('name', 'unknown')
                    if debug:
                        print(f"    [DECORATION COLLISION] '{deco_name}' at {deco_pos}")
                    return (False, deco_name)
        
        if debug and decorations:
            print(f"    [NO DECORATION COLLISION]")
        
        return (True, None)
    
    def _is_tile_walkable(self, tile_id: int) -> bool:
        """
        Check if a specific tile ID is walkable based on tile configuration.
        
        Args:
            tile_id: Tile ID to check
            
        Returns:
            True if tile is walkable, False otherwise
        """
        if tile_id is None:
            return False
        
        # Check if resource_manager has walkable info for this tile
        if self.resource_manager and hasattr(self.resource_manager, 'tile_config'):
            # Try both int and string keys for tile_config
            tile_config = self.resource_manager.tile_config.get(tile_id)
            if tile_config is None:
                tile_config = self.resource_manager.tile_config.get(str(tile_id))
            if tile_config:
                return tile_config.get('walkable', True)
        
        # Default: -1 (void) is not walkable, all others are walkable
        return tile_id != -1
    
    def _get_tile_name(self, tile_id: int) -> str:
        """
        Get the name of a tile for debug logging.
        
        Args:
            tile_id: Tile ID
            
        Returns:
            Name of the tile or "unknown"
        """
        if tile_id is None:
            return "out_of_bounds"
        
        if self.resource_manager and hasattr(self.resource_manager, 'tile_config'):
            # Try both int and string keys for tile_config
            tile_config = self.resource_manager.tile_config.get(tile_id)
            if tile_config is None:
                tile_config = self.resource_manager.tile_config.get(str(tile_id))
            if tile_config:
                return tile_config.get('name', 'unknown')
        
        if tile_id == -1:
            return "void"
        
        return f"tile_{tile_id}"

