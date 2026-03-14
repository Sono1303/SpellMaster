"""
Resource Manager Module - Spell Master Asset Loading
Centralized management of game resources including images, sounds, fonts, and sprite sheets.

Classes:
    ResourceManager: Loads and caches game assets from files and JSON sprite sheet definitions
"""

import pygame
import json
from pathlib import Path
from typing import Optional, Dict, Tuple, List


class ResourceManager:
    """
    Manages loading, caching, and retrieval of game resources.
    
    Resources are loaded once and cached in memory to optimize performance.
    Supports images, sounds, and fonts.
    """
    
    def __init__(self, asset_dir: Path):
        """
        Initialize the ResourceManager.
        
        Args:
            asset_dir: Path to the main assets directory
        """
        self.asset_dir = Path(asset_dir)
        self.images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.fonts: Dict[str, pygame.font.Font] = {}
        self.asset_cache: Dict[str, pygame.Surface] = {}  # Sprite cache from JSON
        self.asset_sizes: Dict[str, Tuple[int, int]] = {}  # Store (width, height) for each asset
        self.tile_config: Dict[int, Dict] = {}  # Tile configuration from JSON
    
    def load_image(self, filename: str, subdir: str = "") -> pygame.Surface:
        """
        Load an image file. Returns cached version if already loaded.
        
        Args:
            filename: Name of the image file
            subdir: Optional subdirectory within assets (e.g., 'tiles', 'sprites')
            
        Returns:
            pygame.Surface: The loaded image
            
        Raises:
            FileNotFoundError: If image file not found
        """
        cache_key = f"{subdir}/{filename}" if subdir else filename
        
        if cache_key in self.images:
            return self.images[cache_key]
        
        if subdir:
            filepath = self.asset_dir / subdir / filename
        else:
            filepath = self.asset_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Image not found: {filepath}")
        
        try:
            image = pygame.image.load(str(filepath))
            self.images[cache_key] = image
            return image
        except pygame.error as e:
            raise pygame.error(f"Failed to load image {filename}: {e}")
    
    def get_image(self, filename: str, subdir: str = "") -> pygame.Surface:
        """
        Get an image (from cache or load if not cached).
        
        Args:
            filename: Name of the image file
            subdir: Optional subdirectory within assets
            
        Returns:
            pygame.Surface: The image
        """
        return self.load_image(filename, subdir)
    
    def load_sound(self, filename: str, subdir: str = "") -> pygame.mixer.Sound:
        """
        Load a sound file. Returns cached version if already loaded.
        
        Args:
            filename: Name of the sound file
            subdir: Optional subdirectory within assets
            
        Returns:
            pygame.mixer.Sound: The loaded sound
            
        Raises:
            FileNotFoundError: If sound file not found
        """
        cache_key = f"{subdir}/{filename}" if subdir else filename
        
        if cache_key in self.sounds:
            return self.sounds[cache_key]
        
        if subdir:
            filepath = self.asset_dir / subdir / filename
        else:
            filepath = self.asset_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Sound not found: {filepath}")
        
        try:
            sound = pygame.mixer.Sound(str(filepath))
            self.sounds[cache_key] = sound
            return sound
        except pygame.error as e:
            raise pygame.error(f"Failed to load sound {filename}: {e}")
    
    def get_sound(self, filename: str, subdir: str = "") -> pygame.mixer.Sound:
        """
        Get a sound (from cache or load if not cached).
        
        Args:
            filename: Name of the sound file
            subdir: Optional subdirectory
            
        Returns:
            pygame.mixer.Sound: The sound
        """
        return self.load_sound(filename, subdir)
    
    def load_font(self, filename: str, size: int, subdir: str = "") -> pygame.font.Font:
        """
        Load a font file.
        
        Args:
            filename: Name of the font file
            size: Font size in pixels
            subdir: Optional subdirectory
            
        Returns:
            pygame.font.Font: The loaded font
        """
        cache_key = f"{subdir}/{filename}_{size}" if subdir else f"{filename}_{size}"
        
        if cache_key in self.fonts:
            return self.fonts[cache_key]
        
        if subdir:
            filepath = self.asset_dir / subdir / filename
        else:
            filepath = self.asset_dir / filename
        
        try:
            font = pygame.font.Font(str(filepath), size)
            self.fonts[cache_key] = font
            return font
        except pygame.error as e:
            raise pygame.error(f"Failed to load font {filename}: {e}")
    
    def get_font(self, filename: str, size: int, subdir: str = "") -> pygame.font.Font:
        """
        Get a font (from cache or load if not cached).
        
        Args:
            filename: Name of the font file
            size: Font size
            subdir: Optional subdirectory
            
        Returns:
            pygame.font.Font: The font
        """
        return self.load_font(filename, size, subdir)
    
    # ========================================================================
    # SPRITE SHEET MANAGEMENT (JSON-based asset loading)
    # ========================================================================
    
    def _create_placeholder_image(self, width: int = 64, height: int = 64) -> pygame.Surface:
        """
        Create a pink placeholder image for missing assets.
        
        Args:
            width: Width in pixels
            height: Height in pixels
            
        Returns:
            pygame.Surface: Pink placeholder surface
        """
        surface = pygame.Surface((width, height))
        surface.fill((255, 100, 200))  # Bright pink
        return surface
    
    def load_all_assets(self, json_path: str) -> bool:
        """
        Load all sprites from a JSON sprite sheet definition file.
        
        JSON Structure:
        {
            "sprite_sheets": [
                {
                    "file_path": "path/to/spritesheet.png",
                    "assets": [
                        {"name": "sprite_name", "rect": [x, y, w, h]},
                        ...
                    ]
                },
                ...
            ]
        }
        
        Each sprite is loaded from the sheet using rect coordinates and stored
        in asset_cache with 'name' as the key. If a file or rect is invalid,
        a pink placeholder is stored instead.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            bool: True if loading succeeded, False otherwise
        """
        json_file = Path(json_path)
        if not json_file.exists():
            print(f"✗ JSON file not found: {json_path}")
            return False
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            sprite_sheets = data.get("sprite_sheets", [])
            print(f"Loading assets from {len(sprite_sheets)} sprite sheet(s)...")
            
            for sheet_idx, sheet_data in enumerate(sprite_sheets):
                file_path = sheet_data.get("file_path")
                assets = sheet_data.get("assets", [])
                
                if not file_path:
                    print(f"  ⚠ Sheet {sheet_idx}: Missing file_path, skipping")
                    continue
                
                # Resolve file path relative to JSON file directory
                sheet_path = json_file.parent / file_path
                if not sheet_path.exists():
                    print(f"  ✗ Sheet {sheet_idx}: File not found: {sheet_path}")
                    continue
                
                # Load sprite sheet image once
                try:
                    spritesheet = pygame.image.load(str(sheet_path))
                    print(f"  ✓ Loaded sprite sheet: {sheet_path}")
                    print(f"    Size: {spritesheet.get_width()}×{spritesheet.get_height()} pixels")
                except pygame.error as e:
                    print(f"  ✗ Failed to load sprite sheet {sheet_path}: {e}")
                    continue
                
                # Extract individual sprites
                for asset_data in assets:
                    name = asset_data.get("name")
                    rect = asset_data.get("rect")
                    
                    if not name or not rect:
                        print(f"    ⚠ Invalid asset data: {asset_data}")
                        continue
                    
                    try:
                        x, y, w, h = rect
                        
                        # Validate rect bounds
                        if x < 0 or y < 0 or w <= 0 or h <= 0:
                            raise ValueError(f"Invalid rect dimensions: {rect}")
                        
                        if x + w > spritesheet.get_width() or y + h > spritesheet.get_height():
                            raise ValueError(
                                f"Rect {rect} exceeds sheet size "
                                f"{spritesheet.get_width()}×{spritesheet.get_height()}"
                            )
                        
                        # Crop sprite from sheet - preserve alpha channel
                        sprite_surface = pygame.Surface((w, h), pygame.SRCALPHA)
                        sprite_surface.blit(spritesheet, (0, 0), pygame.Rect(x, y, w, h))
                        
                        # Store in cache
                        self.asset_cache[name] = sprite_surface
                        self.asset_sizes[name] = (w, h)
                        print(f"    ✓ {name}: {w}×{h}px at ({x}, {y})")
                    
                    except (ValueError, TypeError) as e:
                        print(f"    ✗ Error loading '{name}': {e}")
                        # Create pink placeholder
                        w = rect[2] if len(rect) > 2 else 64
                        h = rect[3] if len(rect) > 3 else 64
                        self.asset_cache[name] = self._create_placeholder_image(w, h)
                        self.asset_sizes[name] = (w, h)
            
            # Load tile configuration from JSON
            tile_config_data = data.get("tile_configuration", {})
            if tile_config_data:
                print("Loading tile configuration...")
                for tile_id_str, tile_data in tile_config_data.items():
                    try:
                        tile_id = int(tile_id_str)
                        color = tile_data.get("color", [0, 0, 0])
                        self.tile_config[tile_id] = {
                            "name": tile_data.get("name", "unknown"),
                            "asset_name": tile_data.get("asset_name"),
                            "walkable": tile_data.get("walkable", False),
                            "color": tuple(color) if isinstance(color, list) else color,
                            "defense_modifier": tile_data.get("defense_modifier", 0.0),
                        }
                        print(f"  ✓ Tile {tile_id}: {self.tile_config[tile_id]['name']}")
                    except (ValueError, KeyError) as e:
                        print(f"  ✗ Error loading tile config for {tile_id_str}: {e}")
                print()
            
            print(f"\n✓ Total assets loaded: {len(self.asset_cache)}\n")
            return True
        
        except json.JSONDecodeError as e:
            print(f"✗ JSON parse error in {json_path}: {e}")
            return False
        except Exception as e:
            print(f"✗ Error loading assets: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_asset(self, name: str) -> Optional[pygame.Surface]:
        """
        Get a sprite asset from the cache.
        
        Args:
            name: Name of the asset (as defined in JSON)
            
        Returns:
            pygame.Surface if found, None otherwise
        """
        return self.asset_cache.get(name)
    
    def get_asset_size(self, name: str) -> Optional[Tuple[int, int]]:
        """
        Get the dimensions of a sprite asset.
        
        This is crucial for correct sprite positioning. Different sprites have
        different sizes (e.g., 66×99 for stairs, 10×100 for pillars), so you
        need to know the real dimensions to:
        
        1. Calculate drawing position correctly:
           - If drawing at (x, y) as top-left: just use pos = (x, y)
           - If drawing at (x, y) as center: offset by (width/2, height/2)
           - If drawing at (x, y) as bottom-left: offset Y by height
        
        2. Handle sprite-to-world coordinate conversion:
           - Tile-based: count tiles and multiply by tile_size
           - Pixel-based: direct pixel coordinates
           - Camera offset: add camera position to convert world to screen
        
        Args:
            name: Name of the asset
            
        Returns:
            Tuple (width, height) if found, None otherwise
            
        Example:
            size = resource_manager.get_asset_size("stone_stair_1")
            if size:
                w, h = size
                screen_x = world_x  # or apply camera offset
                screen_y = world_y - h  # offset to place on ground
                render(asset, screen_x, screen_y)
        """
        return self.asset_sizes.get(name)
    
    def list_assets(self) -> List[str]:
        """
        Get a list of all loaded asset names.
        
        Returns:
            List of asset names
        """
        return list(self.asset_cache.keys())
    
    def get_tile_config(self, tile_id: int) -> Optional[Dict]:
        """
        Get the configuration for a tile type.
        
        Args:
            tile_id: Tile ID (e.g., 0 for grass, 1 for path, -1 for void)
            
        Returns:
            Dictionary with tile config (name, asset_name, walkable, color, defense_modifier)
            or None if not found
            
        Example:
            config = resource_manager.get_tile_config(0)
            if config:
                asset_name = config["asset_name"]
                sprite = resource_manager.get_asset(asset_name)
        """
        return self.tile_config.get(tile_id)
        """Clear all cached resources to free memory."""
        self.images.clear()
        self.sounds.clear()
        self.fonts.clear()
        self.asset_cache.clear()
        self.asset_sizes.clear()
