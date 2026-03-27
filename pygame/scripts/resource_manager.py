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
        self.collision_config: Dict[str, Dict] = {}  # Collision dimensions for decorations from JSON
    
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
            
            # Load collision configuration from JSON
            collision_config_data = data.get("collision_config", {})
            if collision_config_data:
                print("Loading collision configuration...")
                for asset_name, collision_data in collision_config_data.items():
                    try:
                        width = collision_data.get("width", 64)
                        height = collision_data.get("height", 64)
                        self.collision_config[asset_name] = {
                            "width": width,
                            "height": height,
                        }
                        print(f"  ✓ {asset_name}: {width}×{height}px")
                    except (ValueError, KeyError) as e:
                        print(f"  ✗ Error loading collision config for '{asset_name}': {e}")
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
        different sizes (e.g., 66×99 for stairs, 10×100 for statues), so you
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
    
    def get_collision_dimensions(self, asset_name: str) -> Optional[Tuple[int, int]]:
        """
        Get collision dimensions (width, height) for a decoration asset.
        
        Args:
            asset_name: Name of the asset
            
        Returns:
            Tuple (width, height) if found, (64, 64) as default, None if not configured
        """
        if asset_name in self.collision_config:
            config = self.collision_config[asset_name]
            return (config.get("width", 64), config.get("height", 64))
        return None
    
    
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


# ============================================================================
# ANIMATION CACHE
# ============================================================================

class AnimationCache:
    """
    Manages animation sequences loaded from JSON configuration (grid-based extraction).
    
    Similar to vfx_library.extract_sprites(), this system divides sprite sheets into
    a regular grid and extracts frames sequentially from a starting position.
    
    An animation is defined by:
    - sprite_sheet: Path to the sprite sheet image
    - grid_rows: Total number of rows in the sprite sheet grid
    - grid_cols: Total number of columns in the sprite sheet grid
    - start_row: Row index to start extracting from (0-indexed)
    - start_col: Column index to start extracting from (0-indexed)
    - frame_count: Number of frames to extract
    
    FRAME EXTRACTION (Grid-Based):
    1. Sprite sheet is divided into equal cells: grid_rows × grid_cols
    2. Each cell size: frame_width = sheet_width / grid_cols, frame_height = sheet_height / grid_rows
    3. Frames are extracted sequentially: left-to-right, then wrap to next row
    
    Example:
        Sprite sheet: 651×77 pixels, grid: 1 row × 10 cols
        - Frame size: 651/10 = 65px wide, 77/1 = 77px tall
        - start_row=0, start_col=0, frame_count=7 → extracts 7 frames from left
        - start_row=0, start_col=3, frame_count=4 → extracts 4 frames starting at column 3
    
    COORDINATE SYSTEM:
    The sprite sheet grid is addressed as [row][col]:
    - Top-left corner is [0][0]
    - Rows increase downward
    - Columns increase rightward
    - Frames are extracted left-to-right, wrapping to next row when needed
    
    Usage Example:
        cache = AnimationCache()
        cache.load_animations_from_json("animations_config.json")
        
        # Get animation frames
        idle_frames = cache.get_animation("wizard", "idle")
        
        # Play animation by indexing
        current_frame_index = 0
        sprite = idle_frames[current_frame_index]
        screen.blit(sprite, (x, y))
    """
    
    def __init__(self):
        """Initialize the AnimationCache."""
        self.animations: Dict[str, Dict[str, List[pygame.Surface]]] = {}
        # Structure: animations[entity_name][animation_name] = [frame1, frame2, ...]
        self.animation_scales: Dict[str, Dict[str, float]] = {}
        # Structure: animation_scales[entity_name][animation_name] = scale_factor
        self.animation_durations: Dict[str, Dict[str, float]] = {}
        # Structure: animation_durations[entity_name][animation_name] = frame_duration
        self.spritesheet_cache: Dict[str, pygame.Surface] = {}
        # Cache loaded sprite sheets to avoid reloading
    
    def load_animations_from_json(self, json_path: str) -> bool:
        """
        Load all animations from a JSON configuration file (grid-based format).
        
        JSON Structure:
        {
            "animations": {
                "wizard": {
                    "idle": {
                        "sprite_sheet": "path/to/wizard_idle.png",
                        "grid_rows": 1,         # Total rows in sprite sheet
                        "grid_cols": 10,        # Total columns in sprite sheet
                        "start_row": 0,         # Starting row (0-indexed)
                        "start_col": 0,         # Starting column (0-indexed)
                        "frame_count": 7        # Number of frames to extract
                    },
                    "cast_spell": {...}
                },
                "monster": {...}
            }
        }
        
        Returns:
            bool: True if loaded successfully, False otherwise
            
        Raises:
            FileNotFoundError: If JSON file doesn't exist
            json.JSONDecodeError: If JSON is malformed
        """
        json_file = Path(json_path)
        if not json_file.exists():
            print(f"✗ Animations JSON not found: {json_path}")
            return False
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            animations_data = data.get("animations", {})
            print(f"Loading animations from {len(animations_data)} entities...")
            
            for entity_name, entity_animations in animations_data.items():
                self.animations[entity_name] = {}
                print(f"\n  Entity: {entity_name}")
                
                for anim_name, anim_config in entity_animations.items():
                    try:
                        spritesheet_path = anim_config.get("sprite_sheet")
                        grid_rows = anim_config.get("grid_rows", 1)
                        grid_cols = anim_config.get("grid_cols", 10)
                        start_row = anim_config.get("start_row", 0)
                        start_col = anim_config.get("start_col", 0)
                        frame_count = anim_config.get("frame_count", 1)
                        scale = anim_config.get("scale", 1.0)  # Default scale 1.0 (no scaling)
                        
                        if not spritesheet_path:
                            print(f"    ⚠ Invalid config for {anim_name}: missing sprite_sheet")
                            continue
                        
                        # Resolve sprite sheet path relative to JSON file
                        sheet_path = json_file.parent / spritesheet_path
                        if not sheet_path.exists():
                            print(f"    ✗ Sprite sheet not found: {sheet_path}")
                            continue
                        
                        # Load sprite sheet (or get from cache)
                        sheet_key = str(sheet_path)
                        if sheet_key not in self.spritesheet_cache:
                            try:
                                spritesheet = pygame.image.load(str(sheet_path))
                                self.spritesheet_cache[sheet_key] = spritesheet
                                print(f"    ✓ Loaded sprite sheet: {sheet_path.name}")
                            except pygame.error as e:
                                print(f"    ✗ Failed to load sprite sheet: {e}")
                                continue
                        else:
                            spritesheet = self.spritesheet_cache[sheet_key]
                        
                        # Extract animation frames
                        frames = self._extract_animation_frames(
                            spritesheet, grid_rows, grid_cols, start_row, start_col, frame_count
                        )
                        
                        # Apply scale if needed
                        if scale != 1.0:
                            frames = self._scale_frames(frames, scale)
                        
                        # Store frames and scale metadata
                        self.animations[entity_name][anim_name] = frames
                        
                        if entity_name not in self.animation_scales:
                            self.animation_scales[entity_name] = {}
                        self.animation_scales[entity_name][anim_name] = scale

                        if entity_name not in self.animation_durations:
                            self.animation_durations[entity_name] = {}
                        self.animation_durations[entity_name][anim_name] = anim_config.get("frame_duration", 0.15)
                        
                        print(f"    ✓ {anim_name}: {len(frames)} frames (scale: {scale})")
                    
                    except Exception as e:
                        print(f"    ✗ Error loading animation {anim_name}: {e}")
            
            return True
        
        except json.JSONDecodeError as e:
            print(f"✗ JSON parse error: {e}")
            return False
        except Exception as e:
            print(f"✗ Error loading animations: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _scale_frames(self, frames: List[pygame.Surface], scale: float) -> List[pygame.Surface]:
        """
        Scale all frames by the given factor.
        
        Args:
            frames: List of pygame.Surface frames
            scale: Scale factor (1.0 = original, 2.0 = 2x larger, 0.5 = half size)
        
        Returns:
            List of scaled pygame.Surface frames
        """
        if scale <= 0:
            scale = 1.0
        
        scaled_frames = []
        for frame in frames:
            if scale == 1.0:
                scaled_frames.append(frame)
            else:
                new_width = int(frame.get_width() * scale)
                new_height = int(frame.get_height() * scale)
                scaled_frame = pygame.transform.scale(frame, (new_width, new_height))
                scaled_frames.append(scaled_frame)
        
        return scaled_frames
    
    def _extract_animation_frames(
        self,
        spritesheet: pygame.Surface,
        grid_rows: int,
        grid_cols: int,
        start_row: int,
        start_col: int,
        frame_count: int
    ) -> List[pygame.Surface]:
        """
        Extract animation frames from a sprite sheet using grid-based division.
        
        Similar to vfx_library.extract_sprites(), divides sprite sheet into equal cells
        based on grid dimensions, then extracts frames sequentially.
        
        Args:
            spritesheet: The sprite sheet surface
            grid_rows: Total number of rows in the sprite sheet grid
            grid_cols: Total number of columns in the sprite sheet grid
            start_row: Starting row index (0-indexed)
            start_col: Starting column index (0-indexed)
            frame_count: Number of frames to extract (left-to-right, wrapping down)
        
        Returns:
            List of pygame.Surface for each frame
            
        Example:
            Sprite sheet 651×77px with 1 row, 10 cols:
            - frame_width = 651 / 10 = 65px
            - frame_height = 77 / 1 = 77px
            - start_row=0, start_col=0, frame_count=7 extracts 7 frames from left
        """
        frames = []
        
        # Calculate frame dimensions from grid
        frame_width = spritesheet.get_width() // grid_cols
        frame_height = spritesheet.get_height() // grid_rows
        
        if frame_width == 0 or frame_height == 0:
            print(f"      ✗ Invalid grid: {grid_rows}×{grid_cols} for sheet {spritesheet.get_width()}×{spritesheet.get_height()}")
            return frames
        
        # Extract frames sequentially starting from start_row, start_col
        for i in range(frame_count):
            # Calculate current position (left-to-right, wrapping down)
            linear_pos = start_col + i
            current_row = start_row + (linear_pos // grid_cols)
            current_col = linear_pos % grid_cols
            
            # Check bounds
            if current_row >= grid_rows:
                print(f"      ⚠ Frame {i}: Exceeded grid rows (row {current_row} >= {grid_rows})")
                break
            
            # Convert grid position to pixel coordinates
            pixel_x = current_col * frame_width
            pixel_y = current_row * frame_height
            
            # Crop frame from sprite sheet
            frame_surface = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame_surface.blit(spritesheet, (0, 0), pygame.Rect(pixel_x, pixel_y, frame_width, frame_height))
            frames.append(frame_surface)
        
        return frames
    
    def get_animation(self, entity_name: str, animation_name: str) -> Optional[List[pygame.Surface]]:
        """
        Get an animation sequence by entity and animation name.
        
        Args:
            entity_name: Name of the entity (e.g., "wizard", "monster")
            animation_name: Name of the animation (e.g., "idle", "cast_spell")
        
        Returns:
            List of pygame.Surface frames, or None if animation not found
            
        Example:
            frames = cache.get_animation("wizard", "idle")
            if frames:
                for frame in frames:
                    screen.blit(frame, (x, y))
        """
        return self.animations.get(entity_name, {}).get(animation_name)
    
    def get_frame_count(self, entity_name: str, animation_name: str) -> int:
        """
        Get the number of frames in an animation.
        
        Args:
            entity_name: Name of the entity
            animation_name: Name of the animation
        
        Returns:
            Number of frames, or 0 if animation not found
        """
        frames = self.get_animation(entity_name, animation_name)
        return len(frames) if frames else 0
    
    def get_scale(self, entity_name: str, animation_name: str) -> float:
        """
        Get the scale factor for an animation.
        
        Args:
            entity_name: Name of the entity
            animation_name: Name of the animation
        
        Returns:
            Scale factor (1.0 = original size, 2.0 = 2x larger), or 1.0 if not found
        """
        return self.animation_scales.get(entity_name, {}).get(animation_name, 1.0)
    
    def list_entities(self) -> List[str]:
        """Get list of all loaded entities (wizard, monster, etc)."""
        return list(self.animations.keys())
    
    def list_animations(self, entity_name: str) -> List[str]:
        """Get list of all animations for a specific entity."""
        return list(self.animations.get(entity_name, {}).keys())
