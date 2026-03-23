"""
Main Pygame Module - Spell Master Game Loop
Entry point for the pygame-based game engine. Handles window initialization,
game loop, and rendering.
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
from entity import Player, Monster, Statue, Portal, EntityState


# ============================================================================
# GAME CONFIGURATION
# ============================================================================

FPS = 60
DEBUG_MODE = True                 # Coordinate overlay on screen
DEBUG_COLLISION = False           # Verbose collision logging in console
DRAW_ALL_COLLISION_BOXES = True   # Draw ALL collision boxes for manual editing

# Global state
MOUSE_POS = (0, 0)
DEBUG_FONT = None
ANIMATION_CACHE = None
PLAYER = None
MONSTERS = []
STATUE = None
PORTALS = []
GAME_OVER = False
SPAWN_TIMER = 0.0
SPAWN_DELAY = 3.0
SPAWNED = False

# ============================================================================
# WINDOW CONFIGURATION (Dynamic from map)
# ============================================================================

WINDOW_CONFIG = {
    "scale": 1.0,
    "padding": 0,
    "use_map_size": True,
}

TILE_ASSETS_PATHS = [
    PYGAME_DIR / "assets" / "Texture",
    PYGAME_DIR / "assets" / "game assets",
    PYGAME_DIR / "assets",
    PYGAME_DIR / "ingame_assets" / "map",
]
TILE_ASSETS_DIR = TILE_ASSETS_PATHS[0]

BACKGROUND_COLOR = (34, 139, 34)


# ============================================================================
# INITIALIZATION FUNCTIONS
# ============================================================================

def initialize_pygame() -> pygame.display:
    """Initialize Pygame and create the game window sized to map data."""
    pygame.init()
    pygame.mixer.init()

    global DEBUG_FONT
    DEBUG_FONT = pygame.font.Font(None, 20)

    if WINDOW_CONFIG["use_map_size"]:
        map_rows = len(LEVEL_1_BASE)
        map_cols = len(LEVEL_1_BASE[0]) if LEVEL_1_BASE else 0
        tile_size = MAP_DIMENSIONS["tile_size"]

        padding = WINDOW_CONFIG["padding"]
        scale = WINDOW_CONFIG["scale"]

        window_width = int((map_cols * tile_size + 2 * padding) * scale)
        window_height = int((map_rows * tile_size + 2 * padding) * scale)
    else:
        window_width = 1280
        window_height = 960

    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("Ignite: Spell Master - Pygame Engine")

    print(f"[OK] Pygame initialized: {window_width}x{window_height}px")
    return screen


def initialize_game_resources() -> tuple:
    """Initialize tile manager, tile map, resource manager, animations, and entities."""
    resource_manager = ResourceManager(TILE_ASSETS_DIR)

    assets_json = PYGAME_DIR / "data" / "assets_map.json"
    if assets_json.exists():
        resource_manager.load_all_assets(str(assets_json))

    tile_manager = TileManager(
        asset_dir=TILE_ASSETS_DIR,
        tile_size=MAP_DIMENSIONS["tile_size"],
        search_paths=TILE_ASSETS_PATHS[1:]
    )

    tile_id_to_asset = {}
    for tile_id, tile_cfg in resource_manager.tile_config.items():
        asset_name = tile_cfg.get("asset_name")
        if asset_name:
            tile_id_to_asset[tile_id] = asset_name

    tile_map = TileMap(
        map_data=LEVEL_1_BASE,
        tile_manager=tile_manager,
        tile_id_to_file=tile_id_to_asset,
        tile_size=MAP_DIMENSIONS["tile_size"],
        resource_manager=resource_manager
    )

    global ANIMATION_CACHE, PLAYER, MONSTERS, STATUE, PORTALS

    ANIMATION_CACHE = AnimationCache()
    animations_json = PYGAME_DIR / "data" / "animations_config.json"
    if animations_json.exists():
        ANIMATION_CACHE.load_animations_from_json(str(animations_json))

    # Update decorations with collision dimensions from config
    for decoration in LEVEL_1_OBJECTS:
        asset_name = decoration.get("name")
        collision_dims = resource_manager.get_collision_dimensions(asset_name)
        if collision_dims:
            decoration["width"], decoration["height"] = collision_dims
            if "collision" not in decoration:
                decoration["collision"] = True
        else:
            decoration.setdefault("width", 64)
            decoration.setdefault("height", 64)

    PLAYER = Player(
        x=320, y=240,
        animation_cache=ANIMATION_CACHE,
        name="Wizard"
    )

    # Create portals
    PORTALS = [
        Portal(x=1000, y=190, animation_cache=ANIMATION_CACHE, spawn_offset_x=160, spawn_offset_y=180),
    ]

    MONSTERS = []

    STATUE = Statue(x=156, y=228, resource_manager=resource_manager, max_health=200, target_offset_x=35, target_offset_y=120)

    print(f"[OK] Player: {PLAYER.name} at ({PLAYER.x}, {PLAYER.y})")
    print(f"[OK] Portals: {len(PORTALS)}")
    print(f"[OK] Monsters: {len(MONSTERS)}")
    print(f"[OK] Statue at ({STATUE.x}, {STATUE.y}) HP: {STATUE.max_health}")
    print(f"[OK] Decorations: {len(LEVEL_1_OBJECTS)}")
    return tile_manager, tile_map, resource_manager


# ============================================================================
# GAME LOOP
# ============================================================================

def handle_events() -> bool:
    """Handle pygame events. Returns False if game should quit."""
    global MOUSE_POS

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False

    MOUSE_POS = pygame.mouse.get_pos()
    return True


def update_game_state(dt: float, tile_map=None, debug_collision: bool = False, decorations: list = None):
    """Update player input/movement/animation and monster AI."""
    global GAME_OVER

    if PLAYER:
        PLAYER.handle_input()
        PLAYER.move(tile_map=tile_map, dt=dt, debug=debug_collision, decorations=decorations)
        PLAYER.update(dt)

    for portal in PORTALS:
        portal.update(dt)

    if GAME_OVER:
        return

    # Spawn monster from portal after delay
    global SPAWN_TIMER, SPAWNED
    if not SPAWNED and PORTALS:
        SPAWN_TIMER += dt
        if SPAWN_TIMER >= SPAWN_DELAY:
            portal = PORTALS[0]
            spawn_x = portal.x + portal.spawn_offset_x
            spawn_y = portal.y + portal.spawn_offset_y
            # Position monster so collision center aligns with spawn point
            m = Monster(x=0, y=0, animation_cache=ANIMATION_CACHE, monster_type="orc")
            m.x = spawn_x - m.collision_offset_x - m.collision_width / 2
            m.y = spawn_y - m.collision_offset_y - m.collision_height / 2
            MONSTERS.append(m)
            SPAWNED = True
            print(f"[SPAWN] Monster collision center at ({m.col_x + m.collision_width/2}, {m.col_y + m.collision_height/2})")

    for monster in MONSTERS:
        if monster._dying:
            monster.update(dt)
            continue

        target = None
        dist_statue = float('inf')
        dist_player = float('inf')

        if STATUE and STATUE.is_alive():
            dist_statue = monster.distance_to(STATUE)

        if PLAYER and PLAYER.is_alive():
            dist_player = monster.distance_to(PLAYER)

        # Player blocks path if closer than statue and within aggro range
        if dist_player < dist_statue and dist_player < monster.aggro_range:
            target = PLAYER
        elif dist_statue < monster.aggro_range:
            target = STATUE

        if target:
            monster.is_aggro = True
            dist_target = monster.distance_to(target)
            if dist_target < monster.attack_range:
                monster.attack(target)
            else:
                monster.move_towards(target)
        else:
            monster.is_aggro = False
            monster.vx = 0
            monster.vy = 0
            if monster._hurt_timer <= 0:
                monster.set_state(EntityState.IDLE)

        monster.move(dt, tile_map=tile_map, decorations=decorations)
        monster.update(dt)

    # Check Game Over
    if STATUE and not STATUE.is_alive():
        GAME_OVER = True


def pixel_to_tile(pixel_x: int, pixel_y: int, tile_size: int = 64) -> tuple:
    """Convert pixel coordinates to tile coordinates."""
    return (pixel_x // tile_size, pixel_y // tile_size)


def draw_all_collision_boxes(screen: pygame.Surface, decorations: list):
    """
    Draw collision boxes for ALL decorations with collision=True.
    Red border (2px) + semi-transparent red fill. Label above the box.
    Thin boxes (< 14px) are expanded visually so they remain visible.
    """
    if not decorations:
        return

    fill_color = (255, 0, 0)
    border_color = (255, 0, 0)
    text_color = (255, 255, 0)
    min_visual = 14  # minimum visual height/width for readability

    for decoration in decorations:
        if not decoration.get("collision", False):
            continue

        pos_x, pos_y = decoration.get("pos", (0, 0))
        width = decoration.get("width", 64)
        height = decoration.get("height", 64)
        asset_name = decoration.get("name", "unknown")

        # Actual collision rect (red fill)
        surf = pygame.Surface((width, max(height, 1)))
        surf.set_alpha(80)
        surf.fill(fill_color)
        screen.blit(surf, (pos_x, pos_y))

        # If box is too thin, draw an expanded visual guide (dashed-style)
        draw_h = max(height, min_visual)
        draw_w = max(width, min_visual)
        # Offset so the expanded box is centered on the actual box
        draw_x = pos_x - (draw_w - width) // 2
        draw_y = pos_y - (draw_h - height) // 2

        # Border on expanded rect
        pygame.draw.rect(screen, border_color, (draw_x, draw_y, draw_w, draw_h), 2)

        # Label above the box
        if DEBUG_FONT:
            label = f"{asset_name} ({pos_x},{pos_y}) {width}x{height}"
            text_surf = DEBUG_FONT.render(label, True, text_color)
            # Draw label background for readability
            label_bg = pygame.Surface((text_surf.get_width() + 4, text_surf.get_height() + 2))
            label_bg.fill((0, 0, 0))
            label_bg.set_alpha(160)
            label_y = draw_y - text_surf.get_height() - 4
            screen.blit(label_bg, (draw_x, label_y))
            screen.blit(text_surf, (draw_x + 2, label_y + 1))


def render_frame(screen: pygame.Surface, tile_map: TileMap, resource_manager: ResourceManager = None, decorations: list = None):
    """
    Render order: background -> tiles -> decorations -> entities -> collision debug -> HUD.
    """
    # Background + tiles
    screen.fill(BACKGROUND_COLOR)
    tile_map.render(screen, offset_x=0, offset_y=0)

    # Decorations (skip statue sprite — Statue entity handles its own rendering)
    if resource_manager and decorations:
        for decoration in decorations:
            asset_name = decoration.get("name")
            if asset_name == "statue" and STATUE and STATUE.is_alive():
                continue
            pos = decoration.get("pos", (0, 0))
            sprite = resource_manager.get_asset(asset_name)
            if sprite is not None:
                screen.blit(sprite, pos)

    # Portals (behind entities)
    for portal in PORTALS:
        portal.draw(screen)

    # Entities
    if STATUE:
        STATUE.draw(screen)
    if PLAYER:
        PLAYER.draw(screen)
    for monster in MONSTERS:
        monster.draw(screen)

    # Collision boxes overlay (all objects with collision=True)
    if DRAW_ALL_COLLISION_BOXES and decorations:
        draw_all_collision_boxes(screen, decorations)

    # Draw portal boxes (yellow) + spawn point (green)
    if DRAW_ALL_COLLISION_BOXES:
        for portal in PORTALS:
            px, py = int(portal.x), int(portal.y)
            pw, ph = portal.portal_width, portal.portal_height
            pygame.draw.rect(screen, (255, 255, 0), (px, py, pw, ph), 2)
            if DEBUG_FONT:
                label = f"portal ({px},{py}) {pw}x{ph}"
                screen.blit(DEBUG_FONT.render(label, True, (255, 255, 0)), (px, py - 14))
            # Spawn point marker (green cross)
            sx = int(portal.x + portal.spawn_offset_x)
            sy = int(portal.y + portal.spawn_offset_y)
            pygame.draw.circle(screen, (0, 255, 0), (sx, sy), 6, 2)
            pygame.draw.line(screen, (0, 255, 0), (sx - 8, sy), (sx + 8, sy), 2)
            pygame.draw.line(screen, (0, 255, 0), (sx, sy - 8), (sx, sy + 8), 2)
            if DEBUG_FONT:
                screen.blit(DEBUG_FONT.render(f"spawn ({sx},{sy})", True, (0, 255, 0)), (sx + 10, sy - 6))

    # Draw statue target point (orange cross)
    if DRAW_ALL_COLLISION_BOXES and STATUE:
        tx = int(STATUE.col_x)
        ty = int(STATUE.col_y)
        pygame.draw.circle(screen, (255, 165, 0), (tx, ty), 6, 2)
        pygame.draw.line(screen, (255, 165, 0), (tx - 8, ty), (tx + 8, ty), 2)
        pygame.draw.line(screen, (255, 165, 0), (tx, ty - 8), (tx, ty + 8), 2)
        if DEBUG_FONT:
            screen.blit(DEBUG_FONT.render(f"target ({tx},{ty})", True, (255, 165, 0)), (tx + 10, ty - 6))

    # Draw player collision box (cyan)
    if DRAW_ALL_COLLISION_BOXES and PLAYER:
        px = int(PLAYER.x + PLAYER.collision_offset_x)
        py = int(PLAYER.y + PLAYER.collision_offset_y)
        pygame.draw.rect(screen, (0, 255, 255), (px, py, PLAYER.collision_width, PLAYER.collision_height), 2)

    # Draw monster collision boxes (magenta)
    if DRAW_ALL_COLLISION_BOXES:
        for monster in MONSTERS:
            mx, my = int(monster.col_x), int(monster.col_y)
            mw, mh = monster.collision_width, monster.collision_height
            pygame.draw.rect(screen, (255, 0, 255), (mx, my, mw, mh), 2)
            if DEBUG_FONT:
                label = f"monster ({mx},{my}) {mw}x{mh}"
                screen.blit(DEBUG_FONT.render(label, True, (255, 0, 255)), (mx, my - 14))

    # HUD overlay
    if DEBUG_MODE:
        mouse_x, mouse_y = MOUSE_POS
        tile_x, tile_y = pixel_to_tile(mouse_x, mouse_y, MAP_DIMENSIONS["tile_size"])

        debug_text = f"Pixel: ({mouse_x}, {mouse_y}) | Tile: ({tile_x}, {tile_y})"
        text_surface = DEBUG_FONT.render(debug_text, True, (255, 255, 0))

        text_bg = pygame.Surface((text_surface.get_width() + 10, text_surface.get_height() + 4))
        text_bg.fill((0, 0, 0))
        text_bg.set_alpha(180)
        screen.blit(text_bg, (5, 5))
        screen.blit(text_surface, (10, 7))

    # Game Over overlay
    if GAME_OVER:
        overlay = pygame.Surface(screen.get_size())
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        screen.blit(overlay, (0, 0))

        go_font = pygame.font.Font(None, 72)
        go_text = go_font.render("GAME OVER", True, (255, 0, 0))
        go_rect = go_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(go_text, go_rect)

        sub_font = pygame.font.Font(None, 30)
        sub_text = sub_font.render("The statue has been destroyed! Press ESC to quit.", True, (255, 255, 255))
        sub_rect = sub_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 + 50))
        screen.blit(sub_text, sub_rect)

    pygame.display.flip()


def main():
    """Main game loop."""
    try:
        print("Starting Spell Master Pygame Engine...")
        screen = initialize_pygame()
        clock = pygame.time.Clock()

        print("Loading game resources...")
        try:
            tile_manager, tile_map, resource_manager = initialize_game_resources()
        except Exception as e:
            print(f"Error loading resources: {e}")
            import traceback
            traceback.print_exc()
            tile_map = None

        print("Entering main game loop...")
        running = True

        while running:
            running = handle_events()
            dt = clock.tick(FPS) / 1000.0

            update_game_state(
                dt,
                tile_map=tile_map,
                debug_collision=DEBUG_COLLISION,
                decorations=LEVEL_1_OBJECTS
            )

            if tile_map is not None:
                render_frame(screen, tile_map, resource_manager, LEVEL_1_OBJECTS)
            else:
                screen.fill(BACKGROUND_COLOR)
                pygame.display.flip()

    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pygame.quit()
        print("Pygame shutdown complete")


if __name__ == "__main__":
    main()
