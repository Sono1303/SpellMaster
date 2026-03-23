"""
Main Pygame Module - Spell Master Game Loop
Entry point for the pygame-based game engine. Handles window initialization,
game loop, and rendering.

Parts:
    Part 1: Pygame initialization and basic game loop
    Part 2: Map rendering integration
"""

import pygame
import sys
from pathlib import Path

# Add parent directories to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
PYGAME_DIR = PROJECT_ROOT / "pygame"
AI_CONTROLLER_DIR = PROJECT_ROOT / "ai_controller"
SCRIPTS_DIR = PYGAME_DIR / "scripts"

sys.path.insert(0, str(AI_CONTROLLER_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

# Import configuration and game modules
from map_data import LEVEL_1_BASE, LEVEL_1_OBJECTS, MAP_DIMENSIONS
from map_engine import TileManager, TileMap
from resource_manager import ResourceManager, AnimationCache
from entity import Player, Monster, EntityState


# ============================================================================
# GAME CONFIGURATION
# ============================================================================

FPS = 60  # Target frames per second
DEBUG_MODE = True  # Set to False to disable coordinate display
DEBUG_COLLISION = True  # Set to True to enable detailed collision logging

# Global mouse position for debug overlay
MOUSE_POS = (0, 0)
DEBUG_FONT = None  # Will be initialized in initialize_pygame()

# Animation and entity management
ANIMATION_CACHE = None  # Will be initialized in initialize_game_resources()
PLAYER = None
MONSTERS = []  # List of monster instances
DEBUG_COLLISION_BOXES = []  # Store collision boxes to draw when debugging

# ============================================================================
# WINDOW CONFIGURATION (Dynamic from map)
# ============================================================================
# Window size is automatically calculated from map dimensions
# Adjust these settings to scale or pad the window

WINDOW_CONFIG = {
    "scale": 1.0,           # Scale factor: 1.0 = 100% (original size)
                            # 0.5 = 50% (smaller), 1.5 = 150% (larger)
    "padding": 0,           # Extra padding around map edges (pixels)
    "use_map_size": True,   # True = fit window to map, False = use fixed size
}

# Tile configuration is now loaded from assets_map.json (tile_configuration section)
# No longer need hardcoded TILE_IMAGE_MAP - resource_manager handles all tile assets
# To change tile assets, edit pygame/data/assets_map.json

# Asset directory for tiles - try multiple locations
TILE_ASSETS_PATHS = [
    PYGAME_DIR / "assets" / "Texture",      # Primary: Texture folder
    PYGAME_DIR / "assets" / "game assets",  # Fallback: game assets folder
    PYGAME_DIR / "assets",       
    PYGAME_DIR / "ingame_assets" / "map",        
]
TILE_ASSETS_DIR = TILE_ASSETS_PATHS[0]  # Use primary path

# Background color (fallback if no tiles load)
BACKGROUND_COLOR = (34, 139, 34)  # Forest green


# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_pygame() -> pygame.display:
    """
    Initialize Pygame and create the game window.
    
    Window size is DYNAMICALLY calculated from actual map data (LEVEL_1_BASE),
    not from hardcoded MAP_DIMENSIONS. This means if you change the number of
    rows or columns in the map, the window automatically resizes!
    
    Configuration via WINDOW_CONFIG:
    - scale: Multiply window size (0.5 = 50%, 1.5 = 150%)
    - padding: Extra pixels around map edges
    - use_map_size: True = fit to map, False = fixed size
    
    Formula:
        window_width = (actual_map_width * tile_size + 2*padding) * scale
        window_height = (actual_map_height * tile_size + 2*padding) * scale
    
    Returns:
        pygame.display: The display surface (screen)
    """
    # Initialize Pygame first
    pygame.init()
    pygame.mixer.init()
    
    # Initialize debug font for coordinate display
    global DEBUG_FONT
    DEBUG_FONT = pygame.font.Font(None, 20)  # None = default font, size 20
    
    # Calculate window size from ACTUAL map data (not hardcoded dimensions)
    if WINDOW_CONFIG["use_map_size"]:
        # Get map dimensions from actual data
        map_rows = len(LEVEL_1_BASE)
        map_cols = len(LEVEL_1_BASE[0]) if LEVEL_1_BASE else 0
        tile_size = MAP_DIMENSIONS["tile_size"]
        
        # Calculate pixel size from actual map
        map_pixel_width = map_cols * tile_size
        map_pixel_height = map_rows * tile_size
        
        # Add padding and apply scale
        padding = WINDOW_CONFIG["padding"]
        scale = WINDOW_CONFIG["scale"]
        
        window_width = int((map_pixel_width + 2 * padding) * scale)
        window_height = int((map_pixel_height + 2 * padding) * scale)
        
        size_info = f"map: {map_cols}x{map_rows} tiles x {tile_size}px"
        if padding > 0:
            size_info += f" + {padding}px padding"
        if scale != 1.0:
            size_info += f" x {scale}x scale"
    else:
        # Use fixed size from config
        window_width = 1280
        window_height = 960
        size_info = "fixed size"
    
    # Create the game window
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Ignite: Spell Master - Pygame Engine")
    
    print(f"[OK] Pygame initialized: {window_width}x{window_height}px ({size_info})")
    return screen


def initialize_game_resources() -> tuple:
    """
    Initialize game resources including tile manager and map.
    
    Resources loaded:
    1. Tile manager for rendering tile-based map
    2. Tile map with LEVEL_1_BASE data
    3. Resource manager for sprite assets
    
    To load sprite sheets from JSON:
        # Create a JSON file with sprite sheet definitions
        # (see sprite_sheets.json.example for format)
        resource_manager.load_all_assets("path/to/sprite_sheets.json")
    
    Returns:
        tuple: (tile_manager, tile_map, resource_manager)
    """
    # Initialize resource manager
    resource_manager = ResourceManager(TILE_ASSETS_DIR)
    
    # Load sprite sheets from JSON definition
    assets_json = PYGAME_DIR / "data" / "assets_map.json"
    if assets_json.exists():
        print(f"Loading sprite assets from: {assets_json}")
        resource_manager.load_all_assets(str(assets_json))
    else:
        print(f"⚠ Sprite assets JSON not found at: {assets_json}")
    
    # Initialize tile manager with asset directory and search paths
    tile_manager = TileManager(
        asset_dir=TILE_ASSETS_DIR,
        tile_size=MAP_DIMENSIONS["tile_size"],
        search_paths=TILE_ASSETS_PATHS[1:]  # Pass fallback paths
    )
    
    # Initialize tilemap with level data
    # Map dimensions are automatically calculated from LEVEL_1_BASE
    # (no need to pass map_width/map_height - they're computed dynamically!)
    
    # Build tile_id_to_asset_name mapping from resource_manager tile configuration
    tile_id_to_asset = {}
    for tile_id, tile_cfg in resource_manager.tile_config.items():
        asset_name = tile_cfg.get("asset_name")
        if asset_name:  # Only add if asset_name is defined
            tile_id_to_asset[tile_id] = asset_name
    
    print(f"Tile configuration: {tile_id_to_asset}")
    
    tile_map = TileMap(
        map_data=LEVEL_1_BASE,
        tile_manager=tile_manager,
        tile_id_to_file=tile_id_to_asset,  # Now maps to asset names instead of filenames
        tile_size=MAP_DIMENSIONS["tile_size"],
        resource_manager=resource_manager  # Pass resource_manager to load sprites by asset name
    )
    
    # ====== PART 3: LOAD ANIMATIONS ======
    global ANIMATION_CACHE, PLAYER, MONSTERS
    
    ANIMATION_CACHE = AnimationCache()
    animations_json = PYGAME_DIR / "data" / "animations_config.json"
    if animations_json.exists():
        print(f"\nLoading animations from: {animations_json}")
        ANIMATION_CACHE.load_animations_from_json(str(animations_json))
    else:
        print(f"⚠ Animations JSON not found at: {animations_json}")
    
    # ====== PART 4: CREATE GAME ENTITIES ======
    print("\nInitializing game entities...")
    
    # Update decorations with collision dimensions from config
    collision_enabled = 0
    for decoration in LEVEL_1_OBJECTS:
        asset_name = decoration.get("name")
        collision_dims = resource_manager.get_collision_dimensions(asset_name)
        if collision_dims:
            decoration["width"], decoration["height"] = collision_dims
            # If collision dimensions exist and collision not explicitly set, enable it
            if "collision" not in decoration:
                decoration["collision"] = True
                collision_enabled += 1
        else:
            # Use defaults if not found in config
            decoration.setdefault("width", 64)
            decoration.setdefault("height", 64)
    
    print(f"[OK] Updated {len(LEVEL_1_OBJECTS)} decorations with collision dimensions")
    print(f"[OK] Enabled collision for {collision_enabled} decorations")
    
    # Create player (wizard)
    PLAYER = Player(
        x=320,  # Starting position in pixels
        y=240,
        animation_cache=ANIMATION_CACHE,
        name="Wizard"
    )
    print(f"[OK] Created player: {PLAYER.name} at ({PLAYER.x}, {PLAYER.y})")
    
    # Create monsters
    MONSTERS = [
        Monster(
            x=800,
            y=200,
            animation_cache=ANIMATION_CACHE,
            monster_type="goblin"
        ),
        Monster(
            x=900,
            y=350,
            animation_cache=ANIMATION_CACHE,
            monster_type="goblin"
        ),
    ]
    print(f"[OK] Created {len(MONSTERS)} monsters")
    
    print("Game resources initialized")
    return tile_manager, tile_map, resource_manager


# ============================================================================
# GAME LOOP
# ============================================================================

def handle_events() -> bool:
    """
    Handle pygame events and update mouse position.
    
    Returns:
        bool: False if game should quit, True otherwise
    """
    global MOUSE_POS
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            print("Quit event received")
            return False
        
        # Handle keyboard input
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("ESC key pressed - quitting")
                return False
    
    # Track mouse position for debug overlay
    MOUSE_POS = pygame.mouse.get_pos()
    
    return True


def update_game_state(dt: float, tile_map=None, debug_collision: bool = False, decorations: list = None):
    """
    Update game logic.
    
    Player update sequence:
    1. handle_input() - Get keyboard commands
    2. move() - Apply velocity with collision detection
    3. update() - Advance animation based on movement
    
    Args:
        dt: Delta time in seconds since last frame
        tile_map: TileMap instance for collision detection (optional)
        debug_collision: If True, print collision debug info
        decorations: List of decoration objects with collision info
    """
    # ====== PLAYER UPDATE ======
    if PLAYER:
        # Step 1: Get player input from keyboard
        PLAYER.handle_input()
        
        # Step 2: Move player with collision detection (tiles + decorations)
        PLAYER.move(tile_map=tile_map, dt=dt, debug=debug_collision, decorations=decorations)
        
        # Step 3: Update animation state based on movement
        PLAYER.update(dt)
    
    # ====== MONSTER UPDATE ======
    for monster in MONSTERS:
        # Check aggro on player
        if PLAYER:
            monster.check_aggro(PLAYER)
            
            # If aggro, move towards player
            if monster.is_aggro:
                monster.move_towards(PLAYER, speed=30.0)
        
        monster.update(dt)



def pixel_to_tile(pixel_x: int, pixel_y: int, tile_size: int = 64) -> tuple:
    """
    Convert pixel coordinates to tile coordinates.
    
    Args:
        pixel_x: X position in pixels
        pixel_y: Y position in pixels
        tile_size: Size of one tile in pixels (default 64)
    
    Returns:
        Tuple (tile_x, tile_y)
    """
    tile_x = pixel_x // tile_size
    tile_y = pixel_y // tile_size
    return (tile_x, tile_y)


def detect_collision_obstacles(entity, decorations: list) -> list:
    """
    Detect which decorations are colliding with the entity.
    
    Args:
        entity: Entity object with x, y, collision_box_size (for Player)
        decorations: List of decoration dicts with collision info
    
    Returns:
        List of decoration dicts that are colliding
    """
    colliding = []
    
    # Get entity collision box size
    if hasattr(entity, 'collision_box_size'):
        entity_size = entity.collision_box_size
        entity_rect = pygame.Rect(entity.x, entity.y, entity_size, entity_size)
    elif hasattr(entity, 'width') and hasattr(entity, 'height'):
        entity_rect = pygame.Rect(entity.x, entity.y, entity.width, entity.height)
    else:
        # Default fallback (shouldn't reach here)
        entity_rect = pygame.Rect(entity.x, entity.y, 20, 20)
    
    if DEBUG_COLLISION:
        print(f"[DETECT] Entity at ({entity.x}, {entity.y}), size {entity_size}x{entity_size}")
    
    collision_count = 0
    collision_enabled_count = 0
    for i, decoration in enumerate(decorations):
        has_collision_flag = decoration.get("collision", False)
        
        if has_collision_flag:
            collision_enabled_count += 1
        
        if not has_collision_flag:
            continue
        
        deco_x, deco_y = decoration.get("pos", (0, 0))
        deco_width = decoration.get("width", 64)
        deco_height = decoration.get("height", 64)
        
        deco_rect = pygame.Rect(deco_x, deco_y, deco_width, deco_height)
        
        if entity_rect.colliderect(deco_rect):
            colliding.append(decoration)
            collision_count += 1
            if DEBUG_COLLISION:
                print(f"  ✓ COLLISION: {decoration.get('name')} at ({deco_x}, {deco_y})")
    
    if DEBUG_COLLISION:
        print(f"[DETECT] Collision enabled: {collision_enabled_count}/{len(decorations)} decorations")
        if collision_count == 0:
            print(f"[DETECT] No collision detected")
    
    return colliding


def draw_collision_debug_boxes(screen: pygame.Surface, collision_boxes: list):
    """
    Draw debug visualization for collision boxes.
    
    Args:
        screen: pygame.Surface to draw on
        collision_boxes: List of decoration dicts to draw
    """
    if not collision_boxes:
        print("[DRAW-COLLISION] No collision boxes to draw")
        return
    
    print(f"[DRAW-COLLISION] Drawing {len(collision_boxes)} boxes")
    
    # Cyan color for collision boxes (semi-transparent)
    color = (0, 255, 255)  # Cyan fill
    alpha = 100
    border_color = (255, 0, 0)  # Red border
    
    for decoration in collision_boxes:
        pos_x, pos_y = decoration.get("pos", (0, 0))
        width = decoration.get("width", 64)
        height = decoration.get("height", 64)
        asset_name = decoration.get("name", "unknown")
        
        print(f"  -> {asset_name} at ({pos_x}, {pos_y}) size {width}x{height}")
        
        # Draw filled rectangle with transparency
        collision_surface = pygame.Surface((width, height))
        collision_surface.set_alpha(alpha)
        collision_surface.fill(color)
        screen.blit(collision_surface, (pos_x, pos_y))
        
        # Draw border in RED
        pygame.draw.rect(screen, border_color, (pos_x, pos_y, width, height), 2)
        
        # Draw asset name text
        if DEBUG_FONT:
            text_surface = DEBUG_FONT.render(asset_name, True, border_color)
            screen.blit(text_surface, (pos_x + 2, pos_y + 2))



def render_frame(screen: pygame.Surface, tile_map: TileMap, resource_manager: ResourceManager = None, decorations: list = None):
    """
    Render a frame of the game with tile layer and decoration layer.
    
    Rendering order (bottom to top):
    1. Background color
    2. Tile map (base layer)
    3. Decorations/objects (overlay layer)
    4. Entities (characters with animations)
    5. Debug overlay (collision visualization + coordinates)
    
    Args:
        screen: pygame.Surface to render to
        tile_map: TileMap instance to render
        resource_manager: ResourceManager for accessing sprite assets (optional)
        decorations: List of decoration objects with name and pos (optional)
    """
    print(f"[RENDER-FRAME] DEBUG_MODE={DEBUG_MODE}, PLAYER={PLAYER is not None}, decorations={len(decorations) if decorations else 0}")
    
    # Clear screen with background color
    screen.fill(BACKGROUND_COLOR)
    
    # Render tile layer (base)
    tile_map.render(screen, offset_x=0, offset_y=0)
    
    # Render decoration/object layer (overlay)
    if resource_manager and decorations:
        for decoration in decorations:
            asset_name = decoration.get("name")
            pos = decoration.get("pos", (0, 0))
            
            # Get sprite asset
            sprite = resource_manager.get_asset(asset_name)
            if sprite is not None:
                screen.blit(sprite, pos)
            else:
                print(f"Warning: Asset '{asset_name}' not found in cache")
    
    # Render entities (characters with animations)
    if PLAYER:
        PLAYER.draw(screen)
    
    for monster in MONSTERS:
        monster.draw(screen)
    
    # ====== DEBUG VISUALIZATION ======
    global DEBUG_COLLISION_BOXES
    if DEBUG_MODE:
        print(f"[DEBUG] Checking collision: PLAYER={PLAYER is not None}, decorations={decorations is not None and len(decorations) > 0}")
        # Detect collision obstacles blocking the player
        if PLAYER and decorations:
            print(f"[DEBUG] Calling detect_collision_obstacles()")
            collision_obstacles = detect_collision_obstacles(PLAYER, decorations)
            print(f"[DEBUG] Collision obstacles found: {len(collision_obstacles)}")
            # Keep collision boxes visible - update them each frame
            if collision_obstacles:
                DEBUG_COLLISION_BOXES = collision_obstacles
                if DEBUG_COLLISION:
                    print(f"[RENDER] Updated DEBUG_COLLISION_BOXES: {len(DEBUG_COLLISION_BOXES)} objects")
            else:
                # Clear if no collision
                DEBUG_COLLISION_BOXES = []
        else:
            print(f"[DEBUG] Skipped: PLAYER={PLAYER is not None}, decorations={decorations is not None}")
        
        # Draw coordinate overlay
        mouse_x, mouse_y = MOUSE_POS
        tile_x, tile_y = pixel_to_tile(mouse_x, mouse_y, MAP_DIMENSIONS["tile_size"])
        
        # Create debug text
        debug_text = f"Pixel: ({mouse_x}, {mouse_y}) | Tile: ({tile_x}, {tile_y})"
        if DEBUG_COLLISION_BOXES:
            debug_text += f" | Collision: {len(DEBUG_COLLISION_BOXES)} object(s)"
        
        text_surface = DEBUG_FONT.render(debug_text, True, (255, 255, 0))  # Yellow text for HUD
        
        # Render with semi-transparent background for better readability
        text_bg = pygame.Surface((text_surface.get_width() + 10, text_surface.get_height() + 4))
        text_bg.fill((0, 0, 0))
        text_bg.set_alpha(180)
        screen.blit(text_bg, (5, 5))
        screen.blit(text_surface, (10, 7))
    
    # ====== DRAW COLLISION BOXES - AFTER EVERYTHING ELSE ======
    # This ensures collision boxes appear on top of all layers
    if DEBUG_MODE and DEBUG_COLLISION_BOXES:
        if DEBUG_COLLISION:
            print(f"[RENDER] Drawing {len(DEBUG_COLLISION_BOXES)} collision boxes")
        draw_collision_debug_boxes(screen, DEBUG_COLLISION_BOXES)
    
    # Update display
    pygame.display.flip()


def main():
    """
    Main game loop.
    """
    try:
        # ====== PART 1: PYGAME INITIALIZATION ======
        print("Starting Spell Master Pygame Engine...")
        screen = initialize_pygame()
        clock = pygame.time.Clock()
        
        # ====== PART 2: INITIALIZE GAME RESOURCES ======
        print("Loading game resources...")
        try:
            tile_manager, tile_map, resource_manager = initialize_game_resources()
        except Exception as e:
            print(f"Error loading resources: {e}")
            print("Continuing with placeholder rendering...")
            tile_map = None
        
        # ====== MAIN GAME LOOP ======
        print("Entering main game loop...")
        running = True
        frame_count = 0
        
        while running:
            # Handle events
            running = handle_events()
            
            # Calculate delta time
            dt = clock.tick(FPS) / 1000.0  # Convert milliseconds to seconds
            
            # Update game state (with tile_map for collision detection)
            if tile_map is not None:
                update_game_state(dt, tile_map=tile_map, debug_collision=DEBUG_COLLISION, decorations=LEVEL_1_OBJECTS)
            else:
                update_game_state(dt, debug_collision=DEBUG_COLLISION, decorations=LEVEL_1_OBJECTS)
            
            # Render frame
            if tile_map is not None:
                render_frame(screen, tile_map, resource_manager, LEVEL_1_OBJECTS)
            else:
                # Fallback: just render background
                screen.fill(BACKGROUND_COLOR)
                pygame.display.flip()
            
            frame_count += 1
            
            # Print performance metrics every 60 frames
            # if frame_count % 60 == 0:
            #     fps = clock.get_fps()
            #     print(f"Frame {frame_count}: {fps:.0f} FPS")

        
        print("Game loop ended - shutting down...")
        
    except Exception as e:
        print(f"Fatal error in main loop: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        pygame.quit()
        print("Pygame shutdown complete")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
