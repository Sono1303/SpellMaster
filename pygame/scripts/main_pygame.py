#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from entity import Player, Monster, Statue, Portal, EntityState, STAT_CONFIG
from spell import SpellManager
from sfx_manager import SFXManager
from player_ui import PlayerUI
from spell_bar import SpellBar
from gesture_client import GestureClient
import json

MONSTER_TYPES = list(STAT_CONFIG["monsters"].keys())

_LEVEL_CONFIG_PATH = Path(__file__).parent.parent / "data" / "level_config.json"
with open(_LEVEL_CONFIG_PATH, "r") as _f:
    LEVEL_CONFIG = json.load(_f)


# ============================================================================
# GAME CONFIGURATION
# ============================================================================

FPS = 60
DEBUG_MODE = False                 # Coordinate overlay on screen
DEBUG_COLLISION = False           # Verbose collision logging in console
DRAW_ALL_COLLISION_BOXES = False   # Draw ALL collision boxes for manual editing
SPELL_TEST_MODE = False            # Spawn monsters in center for testing

# Global state
MOUSE_POS = (0, 0)
DEBUG_FONT = None
ANIMATION_CACHE = None
PLAYER = None
MONSTERS = []
STATUE = None
PORTALS = []
GAME_OVER = False
GAME_STARTED = False           # Track if game has begun
WAITING_FOR_START_GESTURE = False  # Waiting for gesture to start game
WAITING_FOR_RESTART_GESTURE = False # Waiting for gesture to restart after game over
GESTURE_START_HOLD_TIME = 0.0   # Track hold duration for start gesture
START_GESTURE_FRAME_COUNT = 0   # Count frames for start/restart gesture
CURRENT_HELD_GESTURE = None     # Store current held gesture name for start/restart
CURRENT_HELD_CONFIDENCE = 0.0   # Store confidence of current held gesture

# Spell casting gesture tracking
CHAINING_GESTURE = None         # Current gesture being held (for spell casting)
CHAINING_FRAME_COUNT = 0        # Number of frames holding same gesture
CHAINING_CONFIDENCE = 0.0       # Confidence level of chaining gesture

SPELL_MANAGER = None
SFX_MANAGER = None
PLAYER_UI = None
SPELL_BAR = None
GESTURE_CLIENT = None  # UDP client for gesture recognition server

# Wave system state (normal mode)
CURRENT_WAVE = 0
WAVE_MONSTERS_LEFT = []       # queue of monster types to spawn this wave
WAVE_SPAWN_TIMER = 0.0
WAVE_SPAWN_DELAY = 3.0
WAVE_CLEAR_TIMER = 0.0       # countdown between waves
WAVE_WAITING = False          # True = waiting for wave_delay before next wave
ALL_WAVES_DONE = False
WAVE_COUNTDOWN = 0.0          # countdown seconds before wave starts
WAVE_COUNTDOWN_ACTIVE = False # True = showing countdown
WAVE_ANNOUNCE_TIMER = 0.0     # timer for "Wave X" text display after spawn starts
WAVE_ANNOUNCE_DURATION = 2.0  # how long to show "Wave X" after countdown ends

# Victory state
VICTORY = False                 # True when all waves cleared AND all monsters dead
VICTORY_COUNTDOWN = 5.0         # 5s countdown before showing restart prompt
VICTORY_COUNTDOWN_ACTIVE = False # True = counting down after victory
VICTORY_SHOW_RESTART = False    # True = countdown finished, show restart gesture prompt

# Gesture recognition spell mapping
# Maps gesture names to actual spell names from stat_config.json
GESTURE_TO_SPELL = {
    "Fire": "fire",
    "Ice": "ice",
    "Lightning": "lightning",
    "Water": "water",
    "Earth": "earth",
    "Air": "air",
    "Light": "light",
    "Dark": "dark",
    "Crystal": "crystal",
    "Phoenix": "phoenix"
}
GESTURE_SPELL_COOLDOWN = 0.0
GESTURE_SPELL_COOLDOWN_TIME = 0.5  # Minimum 0.5s between gesture spells

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

    global ANIMATION_CACHE, PLAYER, MONSTERS, STATUE, PORTALS, SPELL_MANAGER, SFX_MANAGER, PLAYER_UI, SPELL_BAR

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

    player_cfg = STAT_CONFIG["player"]
    statue_cfg = STAT_CONFIG["statue"]

    PLAYER = Player(
        x=player_cfg["spawn"]["x"], y=player_cfg["spawn"]["y"],
        animation_cache=ANIMATION_CACHE,
        name="Wizard"
    )

    PORTALS = []
    for pcfg in LEVEL_CONFIG.get("portals", []):
        PORTALS.append(Portal(
            x=pcfg["x"], y=pcfg["y"],
            animation_cache=ANIMATION_CACHE,
            spawn_offset_x=pcfg.get("spawn_offset_x"),
            spawn_offset_y=pcfg.get("spawn_offset_y"),
        ))

    MONSTERS = []

    STATUE = Statue(x=statue_cfg["spawn"]["x"], y=statue_cfg["spawn"]["y"],
                    resource_manager=resource_manager)

    SFX_MANAGER = SFXManager()
    PLAYER.sfx_manager = SFX_MANAGER
    PLAYER_UI = PlayerUI(PLAYER)
    SPELL_MANAGER = SpellManager(ANIMATION_CACHE, sfx_manager=SFX_MANAGER)
    SPELL_BAR = SpellBar()

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


def _spawn_monster_at_portal(mtype, portal_index=0):
    """Spawn a monster at the specified portal."""
    if not PORTALS:
        return
    portal = PORTALS[portal_index % len(PORTALS)]
    spawn_x = portal.x + portal.spawn_offset_x
    spawn_y = portal.y + portal.spawn_offset_y
    m = Monster(x=0, y=0, animation_cache=ANIMATION_CACHE, monster_type=mtype)
    m.sfx_manager = SFX_MANAGER
    m.x = spawn_x - m.collision_offset_x - m.collision_width / 2
    m.y = spawn_y - m.collision_offset_y - m.collision_height / 2
    MONSTERS.append(m)
    if SFX_MANAGER:
        SFX_MANAGER.play("action", "monster_spawn")
    print(f"[WAVE {CURRENT_WAVE + 1}] Spawned {mtype} at portal {portal_index} ({spawn_x:.0f}, {spawn_y:.0f})")


def _start_wave_countdown(wave_index):
    """Begin countdown for the given wave."""
    global WAVE_COUNTDOWN, WAVE_COUNTDOWN_ACTIVE, WAVE_ANNOUNCE_TIMER
    normal_cfg = LEVEL_CONFIG.get("normal_mode", {})
    WAVE_COUNTDOWN = normal_cfg.get("countdown", 5.0)
    WAVE_COUNTDOWN_ACTIVE = True
    WAVE_ANNOUNCE_TIMER = 0.0
    print(f"[WAVE {wave_index + 1}] Countdown started: {WAVE_COUNTDOWN:.0f}s")


def _begin_wave_spawning(wave_index):
    """Load wave monsters and begin spawning."""
    global WAVE_MONSTERS_LEFT, WAVE_SPAWN_DELAY, WAVE_SPAWN_TIMER
    global WAVE_COUNTDOWN_ACTIVE, WAVE_ANNOUNCE_TIMER
    normal_cfg = LEVEL_CONFIG.get("normal_mode", {})
    waves = normal_cfg.get("waves", [])
    wave = waves[wave_index]
    WAVE_MONSTERS_LEFT = list(wave.get("monsters", []))
    WAVE_SPAWN_DELAY = wave.get("spawn_delay", normal_cfg.get("spawn_delay", 3.0))
    WAVE_SPAWN_TIMER = WAVE_SPAWN_DELAY  # spawn first monster immediately
    WAVE_COUNTDOWN_ACTIVE = False
    WAVE_ANNOUNCE_TIMER = WAVE_ANNOUNCE_DURATION
    print(f"[WAVE {wave_index + 1}/{len(waves)}] Starting — {len(WAVE_MONSTERS_LEFT)} monsters")


def _update_wave_spawn(dt):
    """Wave-based monster spawning for normal mode."""
    global CURRENT_WAVE, WAVE_MONSTERS_LEFT, WAVE_SPAWN_TIMER, WAVE_SPAWN_DELAY
    global WAVE_CLEAR_TIMER, WAVE_WAITING, ALL_WAVES_DONE
    global WAVE_COUNTDOWN, WAVE_COUNTDOWN_ACTIVE, WAVE_ANNOUNCE_TIMER

    if ALL_WAVES_DONE:
        # Check if all monsters are dead for victory
        global VICTORY, VICTORY_COUNTDOWN_ACTIVE
        if not VICTORY:
            alive = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
            if len(alive) == 0:
                VICTORY = True
                VICTORY_COUNTDOWN_ACTIVE = True
                print("[VICTORY] All waves cleared! Victory countdown starting...")
        return

    normal_cfg = LEVEL_CONFIG.get("normal_mode", {})
    waves = normal_cfg.get("waves", [])
    if not waves:
        return

    # Announce timer (ticks down after countdown ends)
    if WAVE_ANNOUNCE_TIMER > 0:
        WAVE_ANNOUNCE_TIMER -= dt

    # Start first wave countdown
    if CURRENT_WAVE == 0 and not WAVE_MONSTERS_LEFT and not WAVE_WAITING \
            and not WAVE_COUNTDOWN_ACTIVE and not MONSTERS:
        _start_wave_countdown(0)

    # Countdown active
    if WAVE_COUNTDOWN_ACTIVE:
        WAVE_COUNTDOWN -= dt
        if WAVE_COUNTDOWN <= 0:
            _begin_wave_spawning(CURRENT_WAVE)
        return

    # Waiting between waves (all monsters dead → start countdown for next)
    if WAVE_WAITING:
        alive = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
        if len(alive) == 0:
            WAVE_CLEAR_TIMER += dt
            wave_delay = normal_cfg.get("wave_delay", 5.0)
            if WAVE_CLEAR_TIMER >= wave_delay:
                WAVE_WAITING = False
                WAVE_CLEAR_TIMER = 0.0
                CURRENT_WAVE += 1
                if CURRENT_WAVE >= len(waves):
                    ALL_WAVES_DONE = True
                    print("[WAVES] All waves complete!")
                    return
                _start_wave_countdown(CURRENT_WAVE)
        return

    # Spawn monsters from queue
    if WAVE_MONSTERS_LEFT:
        WAVE_SPAWN_TIMER += dt
        if WAVE_SPAWN_TIMER >= WAVE_SPAWN_DELAY:
            WAVE_SPAWN_TIMER = 0.0
            entry = WAVE_MONSTERS_LEFT.pop(0)
            mtype = entry["type"]
            portal_idx = entry.get("portal", 0)
            _spawn_monster_at_portal(mtype, portal_idx)

        # Queue empty → wait for all monsters to die before next wave
        if not WAVE_MONSTERS_LEFT:
            WAVE_WAITING = True
            WAVE_CLEAR_TIMER = 0.0


def _update_start_gesture_hold(dt: float):
    """
    Track gesture holding for start/restart sequence (frame-based for speed).
    After ~60 frames of continuous gesture, will trigger start/restart.
    """
    global GESTURE_START_HOLD_TIME, START_GESTURE_FRAME_COUNT, CURRENT_HELD_GESTURE, CURRENT_HELD_CONFIDENCE
    global WAITING_FOR_START_GESTURE, WAITING_FOR_RESTART_GESTURE
    
    if GESTURE_CLIENT:
        spell_event = GESTURE_CLIENT.get_next_spell()
        if spell_event:
            gesture_name = spell_event.get('spell')
            confidence = spell_event.get('confidence', 0)
            
            # Store gesture for use in process_gesture_spells()
            CURRENT_HELD_GESTURE = gesture_name
            CURRENT_HELD_CONFIDENCE = confidence
            
            # Count continuous frames (60 frames ≈ 1.0 second at 60 FPS)
            START_GESTURE_FRAME_COUNT += 1
            GESTURE_START_HOLD_TIME = START_GESTURE_FRAME_COUNT / 60.0  # Convert frame count to time
            
            # Progress indicator at milestones (20, 40, 60, etc frames)
            if START_GESTURE_FRAME_COUNT % 15 == 0 and START_GESTURE_FRAME_COUNT <= 60:
                progress_pct = min(100, int((START_GESTURE_FRAME_COUNT / 60.0) * 100))
                print(f"[HOLD] {gesture_name}: {GESTURE_START_HOLD_TIME:.1f}s / 1.0s [{progress_pct}%]")
        else:
            # Gesture stopped - reset counter if it was building up
            if START_GESTURE_FRAME_COUNT > 0 and START_GESTURE_FRAME_COUNT < 60:
                print(f"[HOLD] Interrupted at {START_GESTURE_FRAME_COUNT} frames")
                START_GESTURE_FRAME_COUNT = 0
                GESTURE_START_HOLD_TIME = 0.0


def process_gesture_spells():
    """
    Process spells detected via gesture recognition server with focus/holding/cast states.
    
    States:
    - "focus": Spell first detected → Select spell in spell bar
    - "holding": Gesture being held → Show chaining animation
    - "cast": Gesture released after 1s → Actually cast the spell
    """
    global GESTURE_CLIENT, PLAYER, SPELL_MANAGER, SPELL_BAR, MONSTERS
    global GAME_STARTED, WAITING_FOR_START_GESTURE, WAITING_FOR_RESTART_GESTURE, GAME_OVER
    global STATUE
    
    if not GESTURE_CLIENT or not PLAYER or not SPELL_MANAGER:
        return
    
    spell_event = GESTURE_CLIENT.get_next_spell()
    
    if not spell_event:
        return
    
    gesture_name = spell_event.get('spell')
    confidence = spell_event.get('confidence', 0)
    spell_state = spell_event.get('state', 'cast')  # ✅ NEW: spell state
    
    # === BEFORE GAME START: Any spell (focus state) starts the game ===
    if not GAME_STARTED and WAITING_FOR_START_GESTURE:
        if spell_state == 'focus':  # Only start on initial focus
            print(f"\n[START] {gesture_name} ({confidence:.1f}%) → Starting game")
            GAME_STARTED = True
            WAITING_FOR_START_GESTURE = False
        return
    
    # === AFTER GAME OVER: Any spell (focus state) restarts the game ===
    if (GAME_OVER or VICTORY_SHOW_RESTART) and WAITING_FOR_RESTART_GESTURE:
        if spell_state == 'focus':  # Only restart on initial focus
            print(f"\n[RESTART] {gesture_name} ({confidence:.1f}%) → Restarting game")
            GAME_OVER = False
            GAME_STARTED = True
            WAITING_FOR_RESTART_GESTURE = False
            VICTORY = False
            VICTORY_COUNTDOWN = 5.0
            VICTORY_COUNTDOWN_ACTIVE = False
            VICTORY_SHOW_RESTART = False
            
            # Clear monsters and reset game variables
            MONSTERS.clear()
            
            # Reset player health and mana
            if PLAYER:
                PLAYER.health = PLAYER.max_health
                PLAYER.mana = PLAYER.max_mana
            
            # Reset statue health
            if STATUE:
                STATUE.health = STATUE.max_health
                STATUE.display_health = float(STATUE.max_health)
            
            # ✅ RESET WAVE SYSTEM to start from Wave 1
            global CURRENT_WAVE, WAVE_MONSTERS_LEFT, WAVE_SPAWN_TIMER, WAVE_CLEAR_TIMER
            global WAVE_WAITING, WAVE_COUNTDOWN, WAVE_COUNTDOWN_ACTIVE, ALL_WAVES_DONE
            global WAVE_ANNOUNCE_TIMER
            
            CURRENT_WAVE = 0
            WAVE_MONSTERS_LEFT = []
            WAVE_SPAWN_TIMER = 0.0
            WAVE_CLEAR_TIMER = 0.0
            WAVE_WAITING = False
            WAVE_COUNTDOWN = 0.0
            WAVE_COUNTDOWN_ACTIVE = False
            WAVE_ANNOUNCE_TIMER = 0.0
            ALL_WAVES_DONE = False
            
            # ✅ RESET KILL COUNTER
            if SPELL_BAR:
                SPELL_BAR.shared_kills = 0
                SPELL_BAR._prev_alive = 0
        
        return
    
    # === DURING GAME: Handle focus/holding/cast states ===
    if GAME_STARTED and not GAME_OVER:
        if gesture_name not in GESTURE_TO_SPELL:
            print(f"[ERROR] {gesture_name} not in gesture mapping")
            return
        
        spell_type = GESTURE_TO_SPELL[gesture_name]
        
        # ✅ FOCUS STATE: Select and focus the spell
        if spell_state == 'focus':
            print(f"[FOCUS] {gesture_name} → Select & Focus spell (searching for: {spell_type})")
            
            # Find spell index by matching spell type name
            spell_index = None
            for idx, (spell_key, spell_config) in enumerate(SPELL_MANAGER.spell_configs.items()):
                config_name = spell_config.get('name', spell_key)
                print(f"  [DEBUG] Checking index {idx}: key={spell_key}, name={config_name}")
                
                # Match by either spell_key or config name
                if spell_key == spell_type or config_name == spell_type:
                    spell_index = idx
                    print(f"  [DEBUG] ✓ Match found! spell_index={spell_index}")
                    break
            
            if spell_index is not None:
                print(f"[FOCUS] Setting selected_spell_index to {spell_index}")
                
                # ✅ FIX: Check if spell is locked BEFORE selecting
                if SPELL_BAR and SPELL_BAR.is_locked(spell_index):
                    print(f"[FOCUS] ✗ {gesture_name} is LOCKED! Need {SPELL_BAR.unlock_values[gesture_name]} kills, have {SPELL_BAR.shared_kills}")
                    SPELL_BAR.try_select(spell_index)  # Show warning
                    return
                
                # Spell is not locked, safe to select
                PLAYER.selected_spell_index = spell_index
                SPELL_MANAGER.selected_spell_index = spell_index  # ✅ Update spell manager too!
                
                # Trigger UI highlight
                if SPELL_BAR:
                    SPELL_BAR.selected_index = spell_index  # ✅ Update spell bar selection
                    SPELL_BAR.trigger_highlight(spell_index)
                
                print(f"[FOCUS] ✓ {gesture_name} selected! Index={spell_index}")
            else:
                print(f"[FOCUS] ✗ Could not find spell index for '{spell_type}'")
                print(f"[FOCUS] Available spells: {list(SPELL_MANAGER.spell_configs.keys())}")
            
            return
        
        # ✅ HOLDING STATE: Show chaining animation
        if spell_state == 'holding':
            # Check if this is the same spell as focused
            if PLAYER.selected_spell_index is not None:
                # ✅ Only trigger animation if not already in CAST_SPELL state
                if PLAYER.state != EntityState.CAST_SPELL:
                    PLAYER.casting_stage = "casting"  # ✅ Prevent update() from overriding state
                    PLAYER.set_state(EntityState.CAST_SPELL, reset_frame=False)
                    print(f"[HOLDING] {gesture_name} - Casting animation started")
                
                # Trigger animation/highlight while holding
                if SPELL_BAR:
                    SPELL_BAR.trigger_highlight(PLAYER.selected_spell_index)
            return
        
        # ✅ CAST STATE: Actually cast the spell
        if spell_state == 'cast':
            print(f"[CAST] {gesture_name} ({confidence:.1f}%) - Casting spell")
            PLAYER.casting_stage = None  # ✅ Reset so update() manages state normally
            
            if spell_type not in SPELL_MANAGER.spell_configs:
                available_spells = list(SPELL_MANAGER.spell_configs.keys())
                print(f"[ERROR] Spell '{spell_type}' not found in spell manager")
                print(f"[ERROR] Available: {available_spells}")
                return
            
            # Try to cast spell by name
            alive = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
            print(f"[SPELL] Targets available: {len(alive)}")
            
            if alive and SPELL_MANAGER.cast_by_name(spell_type, PLAYER, alive):
                print(f"[CAST] ✓ {gesture_name} ({confidence:.1f}%) - SPELL CAST!")
                
                # ✅ Consume kills for special spells + Reset spell selection to prevent continuous casting
                if SPELL_BAR and PLAYER.selected_spell_index is not None:
                    SPELL_BAR.consume_unlock(PLAYER.selected_spell_index)
                    SPELL_BAR.selected_index = None
                
                PLAYER.selected_spell_index = None
                SPELL_MANAGER.selected_spell_index = None
                
                print(f"[CAST] Spell selection reset - Ready for next spell")
            else:
                print(f"[CAST] ✗ {gesture_name} - Failed (no targets or error)")


def update_game_state(dt: float, tile_map=None, debug_collision: bool = False, decorations: list = None):
    """Update player input/movement/animation and monster AI."""
    global GAME_OVER, GAME_STARTED, WAITING_FOR_START_GESTURE, WAITING_FOR_RESTART_GESTURE

    # === BEFORE GAME START: Wait for first gesture ===
    if not GAME_STARTED:
        WAITING_FOR_START_GESTURE = True
        process_gesture_spells()  # Any spell triggers game start
        return
    
    # === VICTORY: Countdown then wait for restart gesture ===
    global VICTORY, VICTORY_COUNTDOWN, VICTORY_COUNTDOWN_ACTIVE, VICTORY_SHOW_RESTART
    if VICTORY:
        if VICTORY_COUNTDOWN_ACTIVE:
            VICTORY_COUNTDOWN -= dt
            if VICTORY_COUNTDOWN <= 0:
                VICTORY_COUNTDOWN_ACTIVE = False
                VICTORY_SHOW_RESTART = True
                WAITING_FOR_RESTART_GESTURE = True
                print("[VICTORY] Countdown finished - waiting for restart gesture")
        if VICTORY_SHOW_RESTART:
            process_gesture_spells()  # Any spell triggers restart
        return

    # === AFTER GAME OVER: Wait for gesture to restart ===
    if GAME_OVER:
        WAITING_FOR_RESTART_GESTURE = True
        process_gesture_spells()  # Any spell triggers restart
        return

    if PLAYER:
        PLAYER.handle_input()
        PLAYER.move(tile_map=tile_map, dt=dt, debug=debug_collision, decorations=decorations, monsters=MONSTERS)
        PLAYER.update(dt)

    if PLAYER_UI:
        PLAYER_UI.update(dt)
    if SPELL_BAR:
        SPELL_BAR.update(dt)
    
    # Process spells from gesture recognition server
    process_gesture_spells()

    # Spell system
    if SPELL_MANAGER and PLAYER:
        # Block selection of locked spells (check for None first)
        if SPELL_BAR and PLAYER.selected_spell_index is not None and SPELL_BAR.is_locked(PLAYER.selected_spell_index):
            SPELL_BAR.try_select(PLAYER.selected_spell_index)
            PLAYER.selected_spell_index = SPELL_MANAGER.selected_spell_index  # revert
        SPELL_MANAGER.selected_spell_index = PLAYER.selected_spell_index

        if PLAYER._spell_ready_to_fire:
            PLAYER._spell_ready_to_fire = False
            if SPELL_BAR and PLAYER.selected_spell_index is not None and SPELL_BAR.is_locked(PLAYER.selected_spell_index):
                SPELL_BAR.try_select(PLAYER.selected_spell_index)
            else:
                alive = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
                if SPELL_MANAGER.cast(PLAYER, alive) and SPELL_BAR:
                    SPELL_BAR.trigger_highlight(PLAYER.selected_spell_index)
                    SPELL_BAR.consume_unlock(PLAYER.selected_spell_index)

        # Track monster kills
        if SPELL_BAR:
            alive_now = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
            new_kills = getattr(SPELL_BAR, '_prev_alive', len(alive_now)) - len(alive_now)
            if new_kills > 0:
                SPELL_BAR.add_kills(new_kills)
            SPELL_BAR._prev_alive = len(alive_now)

        alive = [m for m in MONSTERS if m is not None and m.is_alive() and not m._dying]
        SPELL_MANAGER.update(dt, alive)
        SPELL_MANAGER.update_curse_spread([m for m in MONSTERS if m is not None])

    for portal in PORTALS:
        portal.update(dt)

    # Update statue (smooth HP bar animation)
    if STATUE:
        STATUE.update(dt)

    if GAME_OVER:
        return

    # Remove fully faded monsters (normal mode only; spell test uses fixed slots)
    if not SPELL_TEST_MODE:
        MONSTERS[:] = [m for m in MONSTERS if not m._fully_dead]

    # === SPELL_TEST_MODE: spawn configured monsters in fixed positions ===
    if SPELL_TEST_MODE:
        test_cfg = LEVEL_CONFIG.get("spell_test_mode", {})
        test_types = test_cfg.get("monsters", ["orc"])
        test_count = len(test_types)
        test_spacing = test_cfg.get("spacing", 60)
        map_w = len(LEVEL_1_BASE[0]) * MAP_DIMENSIONS["tile_size"] if LEVEL_1_BASE else 1280
        map_h = len(LEVEL_1_BASE) * MAP_DIMENSIONS["tile_size"] if LEVEL_1_BASE else 960
        center_x = map_w / 2
        center_y = map_h / 2

        # Ensure list always has exactly test_count slots
        while len(MONSTERS) < test_count:
            MONSTERS.append(None)
        while len(MONSTERS) > test_count:
            MONSTERS.pop()

        for slot in range(test_count):
            m = MONSTERS[slot]
            if m is not None and not m._fully_dead:
                continue
            # Respawn at the fixed position for this slot
            offset = (slot - test_count // 2) * test_spacing
            mtype = test_types[slot]
            new_m = Monster(x=0, y=0, animation_cache=ANIMATION_CACHE, monster_type=mtype)
            new_m.sfx_manager = SFX_MANAGER
            new_m.x = center_x + offset - new_m.collision_offset_x - new_m.collision_width / 2
            new_m.y = center_y - new_m.collision_offset_y - new_m.collision_height / 2
            MONSTERS[slot] = new_m
            if SFX_MANAGER:
                SFX_MANAGER.play("action", "monster_spawn")
            print(f"[SPELL_TEST] Spawned {mtype} slot {slot} at ({center_x + offset:.0f}, {center_y:.0f})")
    else:
        # === NORMAL MODE: wave-based spawning ===
        _update_wave_spawn(dt)

    for monster in MONSTERS:
        if monster is None:
            continue
        if monster._dying:
            monster.update(dt)
            continue

        # SPELL_TEST_MODE: monsters stand still as spell targets
        if SPELL_TEST_MODE:
            monster.vx = 0
            monster.vy = 0
            monster.update(dt)
            continue

        # Skip movement if CC locked (stun/freeze/knockup)
        if monster._is_cc_locked():
            monster.vx = 0
            monster.vy = 0
            monster.update(dt)
            continue

        monster._blocked_by_player = False

        # === MODIFIED AGGRO LOGIC ===
        # No dynamic aggro: mobs always move towards statue, never chase player
        monster.is_aggro = False
        if STATUE and STATUE.is_alive():
            monster.move_towards(STATUE)
        else:
            monster.vx = 0
            monster.vy = 0
            if monster._hurt_timer <= 0:
                monster.set_state(EntityState.IDLE)

        old_x = monster.x
        old_y = monster.y
        monster.move(dt, tile_map=tile_map, decorations=decorations, player=PLAYER)

        # Attack logic: priority to statue (proximity), then player (collision block)
        if STATUE and STATUE.is_alive() and monster.is_touching(STATUE, margin=50):
            # Monster reached/touching statue → attack it
            monster.vx = 0
            monster.vy = 0
            monster.attack(STATUE)
        elif (monster.vx != 0 or monster.vy != 0) and (monster.x == old_x or monster.y == old_y) and monster._blocked_by_player and PLAYER and PLAYER.is_alive():
            # Monster tried to move but was blocked by player → attack player
            monster.vx = 0
            monster.vy = 0
            monster.attack(PLAYER)

        monster.update(dt)

    # Check Game Over
    if STATUE and not STATUE.is_alive():
        GAME_OVER = True
    if PLAYER and not PLAYER.is_alive():
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


def _draw_wave_banner(screen):
    """Draw wave countdown, start announcement, and persistent wave indicator."""
    normal_cfg = LEVEL_CONFIG.get("normal_mode", {})
    total_waves = len(normal_cfg.get("waves", []))
    sw = screen.get_width()
    cx = sw // 2
    cy = screen.get_height() // 2

    if WAVE_COUNTDOWN_ACTIVE:
        # Full-width banner: "Wave X" + countdown number
        wave_font = pygame.font.Font(None, 52)
        count_font = pygame.font.Font(None, 80)

        wave_text = wave_font.render(f"Wave {CURRENT_WAVE + 1}", True, (255, 60, 60))
        secs = max(1, int(WAVE_COUNTDOWN) + 1)
        count_text = count_font.render(str(secs), True, (255, 0, 0))

        banner_h = wave_text.get_height() + count_text.get_height() + 24
        banner_y = cy - banner_h // 2

        bg = pygame.Surface((sw, banner_h))
        bg.fill((0, 0, 0))
        bg.set_alpha(160)
        screen.blit(bg, (0, banner_y))

        wr = wave_text.get_rect(centerx=cx, top=banner_y + 8)
        cr = count_text.get_rect(centerx=cx, top=wr.bottom + 4)
        screen.blit(wave_text, wr)
        screen.blit(count_text, cr)

    elif WAVE_ANNOUNCE_TIMER > 0:
        # Full-width banner: "Wave X Start!"
        wave_font = pygame.font.Font(None, 56)
        wave_text = wave_font.render(f"Wave {CURRENT_WAVE + 1} Start!", True, (255, 0, 0))

        banner_h = wave_text.get_height() + 16
        banner_y = cy - banner_h // 2

        alpha = min(160, int(160 * (WAVE_ANNOUNCE_TIMER / WAVE_ANNOUNCE_DURATION)))
        bg = pygame.Surface((sw, banner_h))
        bg.fill((0, 0, 0))
        bg.set_alpha(alpha)
        screen.blit(bg, (0, banner_y))

        wave_text.set_alpha(min(255, int(255 * (WAVE_ANNOUNCE_TIMER / WAVE_ANNOUNCE_DURATION))))
        wr = wave_text.get_rect(centerx=cx, centery=banner_y + banner_h // 2)
        screen.blit(wave_text, wr)

    # Persistent wave indicator — top-right corner
    if not ALL_WAVES_DONE:
        ind_font = pygame.font.Font(None, 36)
        ind_text = ind_font.render(f"Wave {CURRENT_WAVE + 1}/{total_waves}", True, (255, 200, 200))
        ind_bg = pygame.Surface((ind_text.get_width() + 14, ind_text.get_height() + 8))
        ind_bg.fill((0, 0, 0))
        ind_bg.set_alpha(140)
        screen.blit(ind_bg, (sw - ind_bg.get_width() - 8, 8))
        screen.blit(ind_text, (sw - ind_text.get_width() - 15, 12))


def _draw_gesture_start_banner(screen):
    """Draw red banner for start gesture: 'Perform any spell gesture for 1s to start the game'"""
    sw = screen.get_width()
    sh = screen.get_height()
    cx = sw // 2
    cy = sh // 2
    
    main_font = pygame.font.Font(None, 48)
    
    main_text = main_font.render("Perform any spell gesture for 1s", True, (255, 100, 100))
    sub_text = main_font.render("to start the game", True, (255, 100, 100))
    
    # Banner height
    banner_h = main_text.get_height() + sub_text.get_height() + 30
    banner_y = cy - banner_h // 2
    
    # Background
    bg = pygame.Surface((sw, banner_h))
    bg.fill((0, 0, 0))
    bg.set_alpha(160)
    screen.blit(bg, (0, banner_y))
    
    # Draw texts
    mr = main_text.get_rect(centerx=cx, top=banner_y + 10)
    sr = sub_text.get_rect(centerx=cx, top=mr.bottom + 5)
    
    screen.blit(main_text, mr)
    screen.blit(sub_text, sr)


def _draw_victory_screen(screen):
    """Draw victory overlay with countdown or restart prompt."""
    sw = screen.get_width()
    sh = screen.get_height()
    cx = sw // 2
    cy = sh // 2

    # Dark overlay
    overlay = pygame.Surface(screen.get_size())
    overlay.fill((0, 0, 0))
    overlay.set_alpha(150)
    screen.blit(overlay, (0, 0))

    # VICTORY title
    title_font = pygame.font.Font(None, 80)
    title_text = title_font.render("VICTORY", True, (255, 215, 0))  # Gold color
    title_rect = title_text.get_rect(center=(cx, cy - 80))
    screen.blit(title_text, title_rect)

    sub_font = pygame.font.Font(None, 36)
    sub_text = sub_font.render("All waves cleared!", True, (200, 200, 200))
    sub_rect = sub_text.get_rect(center=(cx, cy - 30))
    screen.blit(sub_text, sub_rect)

    if VICTORY_COUNTDOWN_ACTIVE and VICTORY_COUNTDOWN > 0:
        # Show countdown
        cd_font = pygame.font.Font(None, 48)
        cd_text = cd_font.render(f"{int(VICTORY_COUNTDOWN) + 1}", True, (255, 255, 255))
        cd_rect = cd_text.get_rect(center=(cx, cy + 30))
        screen.blit(cd_text, cd_rect)
    elif VICTORY_SHOW_RESTART:
        # Show restart prompt
        prompt_font = pygame.font.Font(None, 40)
        prompt_text = prompt_font.render("Perform any spell gesture for 1s", True, (255, 100, 100))
        prompt_rect = prompt_text.get_rect(center=(cx, cy + 30))
        screen.blit(prompt_text, prompt_rect)

        sub2_font = pygame.font.Font(None, 40)
        sub2_text = sub2_font.render("to play again", True, (255, 100, 100))
        sub2_rect = sub2_text.get_rect(center=(cx, cy + 70))
        screen.blit(sub2_text, sub2_rect)


def _draw_gesture_restart_banner(screen):
    """Draw red banner for restart gesture: 'Perform any spell gesture for 1s to play again'"""
    sw = screen.get_width()
    sh = screen.get_height()
    cx = sw // 2
    cy = sh // 2
    
    main_font = pygame.font.Font(None, 48)
    
    main_text = main_font.render("Perform any spell gesture for 1s", True, (255, 100, 100))
    sub_text = main_font.render("to play again", True, (255, 100, 100))
    
    # Banner height
    banner_h = main_text.get_height() + sub_text.get_height() + 30
    banner_y = cy - banner_h // 2
    
    # Background
    bg = pygame.Surface((sw, banner_h))
    bg.fill((0, 0, 0))
    bg.set_alpha(160)
    screen.blit(bg, (0, banner_y))
    
    # Draw texts
    mr = main_text.get_rect(centerx=cx, top=banner_y + 10)
    sr = sub_text.get_rect(centerx=cx, top=mr.bottom + 5)
    
    screen.blit(main_text, mr)
    screen.blit(sub_text, sr)


def render_frame(screen: pygame.Surface, tile_map: TileMap, resource_manager: ResourceManager = None, decorations: list = None):
    """
    Render order: background -> tiles -> decorations -> entities -> collision debug -> HUD.
    """
    # === BEFORE GAME START: Show start gesture banner ===
    if not GAME_STARTED and WAITING_FOR_START_GESTURE:
        screen.fill(BACKGROUND_COLOR)
        if tile_map:
            tile_map.render(screen, offset_x=0, offset_y=0)
        _draw_gesture_start_banner(screen)
        pygame.display.flip()
        return
    
    # === VICTORY: Show victory screen ===
    if VICTORY:
        screen.fill(BACKGROUND_COLOR)
        if tile_map:
            tile_map.render(screen, offset_x=0, offset_y=0)
        _draw_victory_screen(screen)
        pygame.display.flip()
        return

    # === GAME OVER: Show restart gesture banner ===
    if GAME_OVER and WAITING_FOR_RESTART_GESTURE:
        screen.fill(BACKGROUND_COLOR)
        if tile_map:
            tile_map.render(screen, offset_x=0, offset_y=0)
        
        # Draw game over overlay first
        overlay = pygame.Surface(screen.get_size())
        overlay.fill((0, 0, 0))
        overlay.set_alpha(150)
        screen.blit(overlay, (0, 0))
        
        go_font = pygame.font.Font(None, 72)
        go_text = go_font.render("GAME OVER", True, (255, 0, 0))
        go_rect = go_text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2 - 100))
        screen.blit(go_text, go_rect)
        
        # Then draw restart gesture banner
        _draw_gesture_restart_banner(screen)
        pygame.display.flip()
        return
    
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

    # Entities (monsters first, player on top)
    if STATUE:
        STATUE.draw(screen)
    for monster in MONSTERS:
        if monster is not None:
            monster.draw(screen)
    if PLAYER:
        PLAYER.draw(screen)

    # Active spell effects
    if SPELL_MANAGER:
        SPELL_MANAGER.draw(screen, debug=DRAW_ALL_COLLISION_BOXES)

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
            if monster is None:
                continue
            mx, my = int(monster.col_x), int(monster.col_y)
            mw, mh = monster.collision_width, monster.collision_height
            pygame.draw.rect(screen, (255, 0, 255), (mx, my, mw, mh), 2)
            if DEBUG_FONT:
                label = f"monster ({mx},{my}) {mw}x{mh}"
                screen.blit(DEBUG_FONT.render(label, True, (255, 0, 255)), (mx, my - 14))

    # Player HP/MP UI
    if PLAYER_UI and PLAYER and not GAME_OVER:
        PLAYER_UI.draw(screen)

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

    # Spell icon bar
    if SPELL_BAR and PLAYER and not GAME_OVER:
        SPELL_BAR.draw(screen, PLAYER.selected_spell_index)

    # Wave countdown / announcement banner
    if not SPELL_TEST_MODE and not GAME_OVER:
        _draw_wave_banner(screen)

    pygame.display.flip()


def main():
    """Main game loop."""
    global GESTURE_CLIENT
    
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

        # Initialize gesture recognition client (UDP listener for gesture server)
        print("Starting gesture recognition client...")
        try:
            GESTURE_CLIENT = GestureClient(host='localhost', port=6666)
            GESTURE_CLIENT.start()
            print("[+] Gesture client initialized (listening for spell events)")
        except Exception as e:
            print(f"[!] Warning: Could not start gesture client: {e}")
            print("  Game will run without gesture recognition")
            GESTURE_CLIENT = None

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
        # Cleanup gesture client
        if GESTURE_CLIENT:
            GESTURE_CLIENT.print_stats()
            GESTURE_CLIENT.stop()
        
        pygame.quit()
        print("Pygame shutdown complete")


if __name__ == "__main__":
    main()
