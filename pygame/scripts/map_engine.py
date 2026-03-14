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
