"""
Entity Module - Spell Master Character Management
Defines base Entity class and character types (Player, Monster) with animation support.

Classes:
    Entity: Base class for all game characters with animation and health
    Player: Player-controlled wizard character
    Monster: Enemy monster character
"""

import pygame
import json
import math
from typing import Optional, List, Dict
from enum import Enum
from pathlib import Path

# Load stat config
_STAT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "stat_config.json"
with open(_STAT_CONFIG_PATH, "r") as _f:
    STAT_CONFIG = json.load(_f)


class EntityState(Enum):
    """Entity animation states."""
    IDLE = "idle"
    MOVE = "move"
    WALK = "walk"
    WALK_SIDE = "side_walk"
    WALK_FRONT = "front_walk"
    WALK_BACK = "back_walk"
    ATTACK = "attack"
    ATTACK_1 = "attack_1"
    ATTACK_2 = "attack_2"
    HURT = "hurt"
    DEATH = "death"
    PRE_CAST = "pre_cast_spell"
    CAST_SPELL = "cast_spell"
    POST_CAST = "post_cast_spell"


class Entity:
    """
    Base class for game entities (characters, enemies, etc).
    
    Manages:
    - Position (x, y)
    - Health/HP
    - Animation state and frame playback
    - Rendering
    
    Animation System:
    - Entities have multiple animation sequences (dict of animation names -> frame lists)
    - Each animation has a current_frame_index and elapsed time for frame timing
    - update(dt) advances animation frames based on delta time (frame_duration)
    - draw(surface) renders the current animation frame at entity position
    """
    
    def __init__(
        self,
        x: float,
        y: float,
        max_health: int,
        entity_name: str,
        animation_cache=None,
        initial_state: EntityState = EntityState.IDLE
    ):
        """
        Initialize an Entity.
        
        Args:
            x: X coordinate in pixels
            y: Y coordinate in pixels
            max_health: Maximum health points
            entity_name: Name of entity type (e.g., "wizard", "monster")
                        Used to find animations in animation_cache
            animation_cache: AnimationCache instance for loading animations
            initial_state: Starting animation state (default: IDLE)
        """
        # Position
        self.x = float(x)
        self.y = float(y)
        
        # Health
        self.max_health = max_health
        self.health = max_health
        
        # Animation
        self.entity_name = entity_name
        self.animation_cache = animation_cache
        self.state = initial_state
        self.current_frame_index = 0
        self.elapsed_time = 0.0
        self.frame_duration = 0.1  # Default frame duration (seconds)
        
        # Animation sequences (loaded from cache)
        self.animations: Dict[str, List[pygame.Surface]] = {}
        self._load_animations()
        
        # Velocity (for movement)
        self.vx = 0.0  # Velocity X
        self.vy = 0.0  # Velocity Y
    
    def _load_animations(self):
        """Load all animations for this entity from the animation cache."""
        if not self.animation_cache:
            print(f"⚠ No animation cache provided for {self.entity_name}")
            return
        
        # Get all animation names for this entity
        entity_anims = self.animation_cache.animations.get(self.entity_name, {})
        self.animations = entity_anims
        
        if not self.animations:
            print(f"⚠ No animations found for entity '{self.entity_name}'")
    
    def set_state(self, new_state: EntityState, reset_frame: bool = True):
        """
        Change animation state.
        
        Args:
            new_state: New state to transition to
            reset_frame: If True, reset current_frame_index to 0
        """
        if self.state != new_state:
            self.state = new_state
            if reset_frame:
                self.current_frame_index = 0
                self.elapsed_time = 0.0
    
    def update(self, dt: float):
        """
        Update entity (advance animation frame, update position, etc).
        
        Args:
            dt: Delta time in seconds since last frame
        """
        # Update animation frame based on elapsed time
        self._update_animation_frame(dt)
        
        # Update position based on velocity
        self.x += self.vx * dt
        self.y += self.vy * dt
    
    def _update_animation_frame(self, dt: float):
        """
        Advance animation frame based on elapsed time.
        
        Args:
            dt: Delta time in seconds
        """
        # Get current animation frames
        current_anim = self.animations.get(self.state.value)
        if not current_anim or len(current_anim) == 0:
            return
        
        # Accumulate elapsed time
        self.elapsed_time += dt
        
        # Check if it's time to advance to next frame
        if self.elapsed_time >= self.frame_duration:
            self.elapsed_time -= self.frame_duration
            self.current_frame_index += 1
            
            # Loop animation or stay on last frame
            if self.current_frame_index >= len(current_anim):
                self.current_frame_index = 0  # Loop to beginning
    
    def draw(self, surface: pygame.Surface):
        """
        Draw the entity's current animation frame.
        
        Args:
            surface: pygame.Surface to draw to (typically the screen)
        """
        # Get current animation frames
        current_anim = self.animations.get(self.state.value)
        if not current_anim or len(current_anim) == 0:
            return
        
        # Get current frame
        frame = current_anim[self.current_frame_index % len(current_anim)]
        
        # Draw at entity position
        surface.blit(frame, (int(self.x), int(self.y)))
    
    def take_damage(self, amount: int):
        """
        Reduce health by damage amount.
        
        Args:
            amount: Damage to take
        """
        self.health = max(0, self.health - amount)
    
    def heal(self, amount: int):
        """
        Increase health by heal amount (capped at max_health).
        
        Args:
            amount: Amount to heal
        """
        self.health = min(self.max_health, self.health + amount)
    
    def is_alive(self) -> bool:
        """Check if entity is alive (health > 0)."""
        return self.health > 0
    
    def set_position(self, x: float, y: float):
        """Set entity position."""
        self.x = float(x)
        self.y = float(y)
    
    def get_position(self) -> tuple:
        """Get entity position as (x, y) tuple."""
        return (self.x, self.y)


class Player(Entity):
    """
    Player character (Wizard).
    
    Special properties:
    - Mana for casting spells
    - Experience points
    - Level
    - Velocity-based movement with keyboard input
    - Automatic animation switching based on movement
    - Wall collision detection with wall-sliding
    """
    
    def __init__(
        self,
        x: float,
        y: float,
        animation_cache=None,
        name: str = "Wizard"
    ):
        """
        Initialize the Player.
        
        Args:
            x: Starting X position
            y: Starting Y position
            animation_cache: AnimationCache for animations
            name: Player name (default: "Wizard")
        """
        cfg = STAT_CONFIG["player"]
        col = cfg["collision"]
        super().__init__(
            x=x,
            y=y,
            max_health=cfg["max_health"],
            entity_name="wizard",
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )

        self.name = name
        self.max_mana = cfg["max_mana"]
        self.mana = self.max_mana
        self.mana_regen = cfg.get("mana_regen", 0)
        self.experience = 0
        self.level = 1
        self.frame_duration = cfg["frame_duration"]

        # Movement properties
        self.velocity = pygame.math.Vector2(0, 0)
        self.move_speed = cfg["move_speed"]

        # Collision box
        self.collision_width = col["width"]
        self.collision_height = col["height"]
        self.collision_offset_x = col["offset_x"]
        self.collision_offset_y = col["offset_y"]

        # Casting properties
        self.casting_stage = None  # None, "pre_cast", "casting", or "post_cast"
        self.space_pressed = False  # Track if space is currently held
        self.casting_frame_counter = 0
        self.selected_spell_index = 0  # 0-9 maps to spell keys
        self._spell_ready_to_fire = False  # Consumed by SpellManager
        self.sfx_manager = None  # Set externally after init

    @property
    def col_x(self) -> float:
        return self.x + self.collision_offset_x

    @property
    def col_y(self) -> float:
        return self.y + self.collision_offset_y

    def handle_input(self):
        """
        Handle keyboard input for movement and casting.
        
        Movement (Arrow Keys / WASD):
        - Updates velocity based on input
        - Combines inputs (diagonal movement supported)
        - Left/Right movement uses WALK_SIDE animation (no sprite flipping)
        
        Casting (Space Key):
        - Press down: Start pre-cast animation
        - Hold: Loop cast animation
        - Release: Play post-cast animation
        """
        # Get all keys pressed this frame
        keys = pygame.key.get_pressed()
        
        # ====== MOVEMENT INPUT ======
        # Reset velocity
        self.velocity.x = 0
        self.velocity.y = 0
        
        # Check arrow keys and WASD (no facing_left tracking - use side_walk for left/right)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.velocity.y = -self.move_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.velocity.y = self.move_speed
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.velocity.x = -self.move_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.velocity.x = self.move_speed
        
        # ====== CASTING INPUT ======
        space_now = keys[pygame.K_SPACE]
        
        # Detect space key press (not held from last frame)
        if space_now and not self.space_pressed:
            # Space just pressed - start pre-cast
            self._start_casting()
        
        # Detect space key release
        if not space_now and self.space_pressed:
            # Space just released - transition to post-cast
            self._finish_casting()
        
        self.space_pressed = space_now

        # Spell selection (0-9) while casting
        if self.casting_stage == "casting":
            for i in range(10):
                if keys[getattr(pygame, f'K_{i}')]:
                    self.selected_spell_index = i
                    break

    def move(self, tile_map=None, dt: float = 1.0, debug: bool = False, decorations: list = None, monsters: list = None):
        """
        Move the player based on velocity, with collision detection (tiles + decorations + monsters).

        Performs separate X and Y collision checks for wall-sliding effect.
        If path is blocked on one axis, player can still move on the other.
        """
        if self.velocity.length() == 0:
            return  # No movement

        # Calculate potential new position
        next_x = self.x + self.velocity.x * dt
        next_y = self.y + self.velocity.y * dt

        if debug:
            print(f"[MOVE DEBUG] Current: ({self.x:.1f}, {self.y:.1f}) | Next: ({next_x:.1f}, {next_y:.1f})")

        # Try to move on X axis (with collision check)
        if tile_map is None:
            x_walkable = True
            x_collision_obj = None
        else:
            col_x = next_x + self.collision_offset_x
            col_y = self.y + self.collision_offset_y
            x_walkable, x_collision_obj = self._check_collision(
                col_x, col_y, tile_map, decorations,
                self.collision_width, self.collision_height, debug
            )

        # Check monster collision on X axis (skip if already overlapping — allow escape)
        if x_walkable and monsters:
            cur_rect = pygame.Rect(self.col_x, self.col_y, self.collision_width, self.collision_height)
            next_rect = pygame.Rect(next_x + self.collision_offset_x, self.y + self.collision_offset_y,
                                    self.collision_width, self.collision_height)
            for m in monsters:
                if not m.is_alive() or m._dying:
                    continue
                monster_rect = pygame.Rect(m.col_x, m.col_y, m.collision_width, m.collision_height)
                already_overlapping = cur_rect.colliderect(monster_rect)
                if not already_overlapping and next_rect.colliderect(monster_rect):
                    x_walkable = False
                    x_collision_obj = "monster"
                    break

        if x_walkable:
            self.x = next_x
        elif debug:
            collision_info = f" (blocked by '{x_collision_obj}')" if x_collision_obj else ""
            print(f"    -> X movement BLOCKED{collision_info}")

        # Try to move on Y axis (with collision check)
        if tile_map is None:
            y_walkable = True
            y_collision_obj = None
        else:
            col_x = self.x + self.collision_offset_x
            col_y = next_y + self.collision_offset_y
            y_walkable, y_collision_obj = self._check_collision(
                col_x, col_y, tile_map, decorations,
                self.collision_width, self.collision_height, debug
            )

        # Check monster collision on Y axis (skip if already overlapping — allow escape)
        if y_walkable and monsters:
            cur_rect = pygame.Rect(self.col_x, self.col_y, self.collision_width, self.collision_height)
            next_rect = pygame.Rect(self.x + self.collision_offset_x, next_y + self.collision_offset_y,
                                    self.collision_width, self.collision_height)
            for m in monsters:
                if not m.is_alive() or m._dying:
                    continue
                monster_rect = pygame.Rect(m.col_x, m.col_y, m.collision_width, m.collision_height)
                already_overlapping = cur_rect.colliderect(monster_rect)
                if not already_overlapping and next_rect.colliderect(monster_rect):
                    y_walkable = False
                    y_collision_obj = "monster"
                    break

        if y_walkable:
            self.y = next_y
        elif debug:
            collision_info = f" (blocked by '{y_collision_obj}')" if y_collision_obj else ""
            print(f"    -> Y movement BLOCKED{collision_info}")
    
    def _check_collision(self, pixel_x: float, pixel_y: float, tile_map,
                         decorations: list, col_w: int, col_h: int, debug: bool) -> tuple:
        """
        Check collision at position (tiles + decorations).

        Returns:
            Tuple (is_walkable: bool, collision_name: str or None)
        """
        if hasattr(tile_map, 'is_walkable_with_decorations'):
            return tile_map.is_walkable_with_decorations(
                pixel_x, pixel_y, decorations, col_w, col_h, debug
            )
        else:
            is_walkable = tile_map.is_walkable_pixel(pixel_x, pixel_y, col_w, col_h, debug)
            return (is_walkable, None)
    
    def _get_walk_animation_state(self) -> EntityState:
        """
        Determine which walk animation to use based on velocity direction.
        
        Returns:
            EntityState: WALK_SIDE, WALK_FRONT, or WALK_BACK based on movement direction
            
        Notes:
            - Left/Right movement uses WALK_SIDE (sprite not flipped, animation handles direction)
            - No sprite flipping is used anywhere
        """
        if self.velocity.length() == 0:
            return EntityState.IDLE
        
        abs_vx = abs(self.velocity.x)
        abs_vy = abs(self.velocity.y)
        
        # Determine primary direction
        if abs_vx > abs_vy:
            # Primarily moving horizontally (left or right)
            # Always use WALK_SIDE animation - sprite is never flipped
            return EntityState.WALK_SIDE
        elif self.velocity.y > 0:
            # Primarily moving forward/down
            return EntityState.WALK_FRONT
        else:
            # Primarily moving backward/up
            return EntityState.WALK_BACK
    
    def update(self, dt: float):
        """
        Update player (handle animation state based on movement and casting).
        
        Animation Priority:
        1. Casting animations (PRE_CAST → CAST_SPELL → POST_CAST)
        2. Movement animations (WALK_SIDE, WALK_FRONT, WALK_BACK)
        3. Idle animation
        
        Args:
            dt: Delta time in seconds
        """
        # ===== CASTING STATE MACHINE =====
        if self.casting_stage == "pre_cast":
            # Ensure state is PRE_CAST
            if self.state != EntityState.PRE_CAST:
                self.set_state(EntityState.PRE_CAST, reset_frame=False)
            
            # Check if animation finished and space still held
            current_anim = self.animations.get(EntityState.PRE_CAST.value, [])
            if current_anim and self.current_frame_index >= len(current_anim) - 1 and self.space_pressed:
                # Pre-cast finished and space still held - transition to CAST_SPELL (looping)
                self.casting_stage = "casting"
                self.set_state(EntityState.CAST_SPELL, reset_frame=True)
        
        elif self.casting_stage == "casting":
            # Ensure state is CAST_SPELL (looping animation)
            if self.state != EntityState.CAST_SPELL:
                self.set_state(EntityState.CAST_SPELL, reset_frame=False)
        
        elif self.casting_stage == "post_cast":
            # Ensure state is POST_CAST
            if self.state != EntityState.POST_CAST:
                self.set_state(EntityState.POST_CAST, reset_frame=False)
            
            # Check if post-cast animation finished
            current_anim = self.animations.get(EntityState.POST_CAST.value, [])
            if current_anim and self.current_frame_index >= len(current_anim) - 1:
                # Post-cast animation finished, return to normal movement/idle
                self.casting_stage = None
                if self.velocity.length() > 0:
                    new_state = self._get_walk_animation_state()
                    self.set_state(new_state, reset_frame=True)
                else:
                    self.set_state(EntityState.IDLE, reset_frame=True)
        
        elif self.casting_stage is None:
            # Not casting - handle movement
            if self.velocity.length() > 0:
                # Player is moving - select appropriate walk animation based on direction
                new_state = self._get_walk_animation_state()
                if self.state != new_state:
                    self.set_state(new_state, reset_frame=True)
            else:
                # Player is stationary - use IDLE animation
                if self.state != EntityState.IDLE:
                    self.set_state(EntityState.IDLE, reset_frame=True)
        
        # Mana regen
        if self.mana_regen > 0 and self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen * dt)

        # Call parent update to advance animation frames
        super().update(dt)
    
    def _start_casting(self):
        """
        Start the casting sequence.
        Transitions to PRE_CAST_SPELL animation.
        """
        if self.mana > 0:
            self.casting_stage = "pre_cast"
            self.set_state(EntityState.PRE_CAST, reset_frame=True)
            self.casting_frame_counter = 0
            if self.sfx_manager:
                self.sfx_manager.play("action", "chanting_spell")
            print(f"{self.name} is casting a spell! Mana: {self.mana}")
        else:
            print(f"{self.name} doesn't have enough mana!")
    
    def _finish_casting(self):
        """
        Finish the casting sequence.
        Transitions from CAST_SPELL to POST_CAST_SPELL animation.
        Consumes mana when spell completes.
        """
        if self.casting_stage == "casting" or self.casting_stage == "pre_cast":
            self._spell_ready_to_fire = True
            self.casting_stage = "post_cast"
            self.set_state(EntityState.POST_CAST, reset_frame=True)
            if self.sfx_manager:
                self.sfx_manager.stop("action", "chanting_spell")
    
    def cast_spell(self):
        """
        Initiate spell casting.
        Transitions to CAST_SPELL animation state.
        """
        if self.mana > 0:
            self.set_state(EntityState.CAST_SPELL)
            self.mana -= 0  # Cost per spell
            print(f"{self.name} is casting a spell! Mana: {self.mana}")
        else:
            print(f"{self.name} doesn't have enough mana!")
    
    def regenerate_mana(self, amount: int = 5):
        """
        Regenerate mana.
        
        Args:
            amount: Amount of mana to regenerate
        """
        self.mana = min(self.max_mana, self.mana + amount)
    
    def gain_experience(self, amount: int):
        """
        Gain experience points (can level up).
        
        Args:
            amount: Experience to gain
        """
        self.experience += amount
        
        # Level up every 100 experience
        while self.experience >= 100:
            self.level_up()
    
    def level_up(self):
        """Level up the player."""
        self.level += 1
        self.max_health += 10
        self.health = self.max_health  # Full heal on level up
        self.max_mana += 20
        self.mana = self.max_mana
        print(f"{self.name} leveled up to {self.level}!")
    
    def draw(self, surface: pygame.Surface):
        """
        Draw the player sprite without any flipping.
        
        Position (self.x, self.y) never changes.
        Collision box is always at (self.x, self.y).
        All movement animations (including WALK_SIDE) handle direction visually.
        No sprite flipping is used.
        
        Args:
            surface: pygame.Surface to draw to (typically the screen)
        """
        # Get current animation frames
        current_anim = self.animations.get(self.state.value)
        if not current_anim or len(current_anim) == 0:
            return
        
        # Get current frame
        frame = current_anim[self.current_frame_index % len(current_anim)]
        
        # Draw at entity position - no flipping, no adjustments
        surface.blit(frame, (int(self.x), int(self.y)))




class Monster(Entity):
    """
    Monster enemy character with collision box and full animation states.
    Animations: idle, walk, attack_1, attack_2, hurt, death
    """
    _hp_fill_raw = None
    _hp_border_raw = None

    def __init__(self, x: float, y: float, animation_cache=None,
                 monster_type: str = "orc"):
        cfg = STAT_CONFIG["monsters"].get(monster_type, STAT_CONFIG["monsters"]["orc"])
        col = cfg["collision"]
        super().__init__(
            x=x, y=y,
            max_health=cfg["max_health"],
            entity_name=monster_type,
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )

        self.monster_type = monster_type
        self.attack_damage = cfg["attack_damage"]
        self.aggro_range = cfg["aggro_range"]
        self.is_aggro = False
        self.frame_duration = cfg["frame_duration"]
        self.experience_reward = cfg["experience_reward"]
        self.move_speed = cfg["move_speed"]

        # Attack cooldown
        self.attack_cooldown = cfg["attack_cooldown"]
        self.attack_timer = 0.0

        # Collision box
        self.collision_width = col["width"]
        self.collision_height = col["height"]
        self.collision_offset_x = col["offset_x"]
        self.collision_offset_y = col["offset_y"]

        # Hurt/death state tracking
        self._hurt_timer = 0.0
        self._dying = False
        self._blocked_by_player = False
        self.flipped = True  # Orc sprite faces right by default, flip to face left

        # Death fade-out
        self._fade_timer = -1.0   # counts down from 1.0 after death anim finishes
        self._fade_alpha = 255
        self._fully_dead = False  # True when fade complete → safe to remove

        # HP bar sprites (loaded once, shared across all monsters)
        hp_cfg = cfg.get("hp_bar", {})
        self._hp_bar_w = hp_cfg.get("width", self.collision_width)
        self._hp_bar_h = hp_cfg.get("height", 6)
        self._hp_bar_offset_x = hp_cfg.get("offset_x", 0)
        self._hp_bar_offset_y = hp_cfg.get("offset_y", -4)
        self._hp_pad_x = hp_cfg.get("fill_padding_x", 0)
        self._hp_pad_y = hp_cfg.get("fill_padding_y", 0)
        if Monster._hp_fill_raw is None:
            hp_bar_dir = Path(__file__).parent.parent / "ingame_assets" / "ui" / "mob_hp"
            Monster._hp_fill_raw = pygame.image.load(str(hp_bar_dir / "healthbar.png")).convert_alpha()
            Monster._hp_border_raw = pygame.image.load(str(hp_bar_dir / "hp_border.png")).convert_alpha()
        fill_w = self._hp_bar_w - self._hp_pad_x * 2
        fill_h = self._hp_bar_h - self._hp_pad_y * 2
        self._hp_fill = pygame.transform.scale(Monster._hp_fill_raw, (max(fill_w, 1), max(fill_h, 1)))
        self._hp_border = pygame.transform.scale(Monster._hp_border_raw, (self._hp_bar_w, self._hp_bar_h))

        # Smooth HP bar display
        self.display_health = float(self.max_health)
        self._hp_lerp_speed = 80.0  # HP units per second

        # Status effects
        self._base_move_speed = self.move_speed
        self.cursed = False
        self._status = {
            "burn": {"active": False, "damage": 0, "duration": 0, "timer": 0, "tick_timer": 0},
            "stun": {"active": False, "timer": 0},
            "freeze": {"active": False, "timer": 0, "then_slow_value": 0, "then_slow_duration": 0},
            "slow": {"active": False, "timer": 0, "value": 1.0},
            "knockback": {"active": False, "vx": 0, "vy": 0, "timer": 0},
            "knockup": {"active": False, "duration": 0, "timer": 0, "offset_y": 0},
        }

    @property
    def col_x(self) -> float:
        return self.x + self.collision_offset_x

    @property
    def col_y(self) -> float:
        return self.y + self.collision_offset_y

    def update(self, dt: float):
        self.attack_timer = max(0, self.attack_timer - dt)

        # Smooth HP bar interpolation
        if self.display_health > self.health:
            self.display_health = max(float(self.health),
                                      self.display_health - self._hp_lerp_speed * dt)

        # --- Status effect ticking ---
        burn = self._status["burn"]
        if burn["active"]:
            burn["timer"] -= dt
            burn["tick_timer"] -= dt
            if burn["tick_timer"] <= 0:
                burn["tick_timer"] = 1.0
                self.take_spell_damage(int(burn["damage"]))
            if burn["timer"] <= 0:
                burn["active"] = False

        stun = self._status["stun"]
        if stun["active"]:
            stun["timer"] -= dt
            if stun["timer"] <= 0:
                stun["active"] = False

        freeze = self._status["freeze"]
        if freeze["active"]:
            freeze["timer"] -= dt
            if freeze["timer"] <= 0:
                freeze["active"] = False
                if freeze.get("then_slow_value", 0) > 0:
                    self.apply_slow(freeze["then_slow_value"], freeze.get("then_slow_duration", 0))

        slow = self._status["slow"]
        if slow["active"]:
            slow["timer"] -= dt
            if slow["timer"] <= 0:
                slow["active"] = False
                self.move_speed = self._base_move_speed

        kb = self._status["knockback"]
        if kb["active"]:
            kb["timer"] -= dt
            self.x += kb["vx"] * dt
            self.y += kb["vy"] * dt
            if kb["timer"] <= 0:
                kb["active"] = False

        ku = self._status["knockup"]
        if ku["active"]:
            ku["timer"] -= dt
            progress = 1.0 - (ku["timer"] / ku["duration"]) if ku["duration"] > 0 else 1.0
            ku["offset_y"] = -30 * math.sin(progress * math.pi)
            if ku["timer"] <= 0:
                ku["active"] = False
                ku["offset_y"] = 0

        # If CC locked, only animate, skip AI
        if self._is_cc_locked():
            self._update_animation_frame(dt)
            return

        # Hurt flash duration
        if self._hurt_timer > 0:
            self._hurt_timer -= dt
            if self._hurt_timer <= 0:
                if not self.is_alive() and not self._dying:
                    self._dying = True
                    self.set_state(EntityState.DEATH)
                elif not self._dying:
                    self.set_state(EntityState.IDLE)

        # Death animation — stop after last frame, then fade out
        if self._dying:
            # Already fading → count down fade timer
            if self._fade_timer >= 0:
                self._fade_timer -= dt
                self._fade_alpha = max(0, int(255 * (self._fade_timer / 1.0)))
                if self._fade_timer <= 0:
                    self._fully_dead = True
                return

            death_anim = self.animations.get(EntityState.DEATH.value)
            if death_anim and self.current_frame_index >= len(death_anim) - 1:
                # Death anim finished → start 1s fade
                self._fade_timer = 1.0
                return
            self._update_animation_frame(dt)
            return

        # Attack animation — return to idle when finished
        if self.state in (EntityState.ATTACK_1, EntityState.ATTACK_2):
            attack_anim = self.animations.get(self.state.value)
            if attack_anim and self.current_frame_index >= len(attack_anim) - 1:
                self.set_state(EntityState.IDLE)

        # Normal update
        if self._hurt_timer <= 0:
            self._update_animation_frame(dt)

    def move(self, dt: float, tile_map=None, decorations: list = None, player=None):
        """Move monster with tile + decoration + player collision checking."""
        if self._hurt_timer > 0 or self._dying:
            return
        if self.vx == 0 and self.vy == 0:
            return

        next_x = self.x + self.vx * dt
        next_y = self.y + self.vy * dt

        if tile_map is None and player is None:
            self.x = next_x
            self.y = next_y
            return

        # Build player rect once
        player_rect = None
        if player and player.is_alive():
            player_rect = pygame.Rect(
                player.x + player.collision_offset_x, player.y + player.collision_offset_y,
                player.collision_width, player.collision_height)

        # Check X axis — tiles/decorations
        x_ok = True
        if tile_map:
            col_x = next_x + self.collision_offset_x
            col_y = self.y + self.collision_offset_y
            if hasattr(tile_map, 'is_walkable_with_decorations'):
                x_ok, _ = tile_map.is_walkable_with_decorations(
                    col_x, col_y, decorations, self.collision_width, self.collision_height)
            else:
                x_ok = tile_map.is_walkable_pixel(col_x, col_y, self.collision_width, self.collision_height)

        # Check X axis — player (skip if already overlapping)
        if x_ok and player_rect:
            cur_rect = pygame.Rect(self.col_x, self.col_y, self.collision_width, self.collision_height)
            already_overlapping = cur_rect.colliderect(player_rect)
            if not already_overlapping:
                next_rect = pygame.Rect(
                    next_x + self.collision_offset_x, self.y + self.collision_offset_y,
                    self.collision_width, self.collision_height)
                if next_rect.colliderect(player_rect):
                    x_ok = False
                    self._blocked_by_player = True

        if x_ok:
            self.x = next_x

        # Check Y axis — tiles/decorations
        y_ok = True
        if tile_map:
            col_x = self.x + self.collision_offset_x
            col_y = next_y + self.collision_offset_y
            if hasattr(tile_map, 'is_walkable_with_decorations'):
                y_ok, _ = tile_map.is_walkable_with_decorations(
                    col_x, col_y, decorations, self.collision_width, self.collision_height)
            else:
                y_ok = tile_map.is_walkable_pixel(col_x, col_y, self.collision_width, self.collision_height)

        # Check Y axis — player (skip if already overlapping)
        if y_ok and player_rect:
            cur_rect = pygame.Rect(self.col_x, self.col_y, self.collision_width, self.collision_height)
            already_overlapping = cur_rect.colliderect(player_rect)
            if not already_overlapping:
                next_rect = pygame.Rect(
                    self.x + self.collision_offset_x, next_y + self.collision_offset_y,
                    self.collision_width, self.collision_height)
                if next_rect.colliderect(player_rect):
                    y_ok = False
                    self._blocked_by_player = True

        if y_ok:
            self.y = next_y

    def is_touching(self, target: Entity, margin: int = 5) -> bool:
        """Check if collision boxes are touching or within margin px."""
        tx = getattr(target, 'col_x', target.x)
        ty = getattr(target, 'col_y', target.y)
        tw = max(getattr(target, 'collision_width', 0), 1)
        th = max(getattr(target, 'collision_height', 0), 1)

        expanded = pygame.Rect(
            self.col_x - margin, self.col_y - margin,
            self.collision_width + margin * 2, self.collision_height + margin * 2)
        target_rect = pygame.Rect(tx, ty, tw, th)
        return expanded.colliderect(target_rect)

    def take_damage(self, amount: int):
        super().take_damage(amount)
        if self.is_alive():
            self._hurt_timer = 0.4
            self.set_state(EntityState.HURT)
        else:
            self._hurt_timer = 0.4
            self.set_state(EntityState.HURT)

    def take_spell_damage(self, amount: int):
        """Reduce HP and trigger hurt animation."""
        self.health = max(0, self.health - amount)
        if not self.is_alive() and not self._dying:
            self._hurt_timer = 0.4
            self.set_state(EntityState.HURT)
        elif self.is_alive() and not self._dying:
            self._hurt_timer = 0.4
            self.set_state(EntityState.HURT)

    def apply_burn(self, damage_per_sec: float, duration: float):
        b = self._status["burn"]
        b["active"] = True
        b["damage"] = damage_per_sec
        b["timer"] = max(b["timer"], duration)
        if b["tick_timer"] <= 0:
            b["tick_timer"] = 1.0

    def apply_stun(self, duration: float):
        s = self._status["stun"]
        s["active"] = True
        s["timer"] = max(s["timer"], duration)

    def apply_freeze(self, duration: float, then_slow_value: float = 0, then_slow_duration: float = 0):
        f = self._status["freeze"]
        f["active"] = True
        f["timer"] = max(f["timer"], duration)
        f["then_slow_value"] = then_slow_value
        f["then_slow_duration"] = then_slow_duration

    def apply_slow(self, value: float, duration: float):
        s = self._status["slow"]
        s["active"] = True
        s["value"] = value
        s["timer"] = max(s["timer"], duration)
        self.move_speed = self._base_move_speed * value

    def apply_knockback(self, force: float, dir_x: float, dir_y: float):
        kb = self._status["knockback"]
        kb["active"] = True
        kb["vx"] = dir_x * force
        kb["vy"] = dir_y * force
        kb["timer"] = 0.2

    def apply_knockup(self, duration: float):
        ku = self._status["knockup"]
        ku["active"] = True
        ku["duration"] = duration
        ku["timer"] = duration
        ku["offset_y"] = 0

    def _is_cc_locked(self) -> bool:
        return (self._status["stun"]["active"] or
                self._status["freeze"]["active"] or
                self._status["knockup"]["active"])

    def attack(self, target: Entity):
        """Attack if cooldown ready. Uses attack_1 animation."""
        if self.attack_timer > 0 or self._hurt_timer > 0 or self._dying:
            return
        if isinstance(target, Entity):
            self.set_state(EntityState.ATTACK_1)
            target.take_damage(self.attack_damage)
            self.attack_timer = self.attack_cooldown
            self.vx = 0
            self.vy = 0

    def move_towards(self, target: Entity, speed: float = None):
        """Move straight (horizontal only) towards target."""
        if self._hurt_timer > 0 or self._dying:
            return
        if self.attack_timer > 0:
            self.vx = 0
            self.vy = 0
            return
        speed = speed or self.move_speed
        tx = getattr(target, 'col_x', target.x) + getattr(target, 'collision_width', 0) / 2
        mx = self.col_x + self.collision_width / 2
        dx = tx - mx
        if dx < 0:
            self.vx = -speed
        elif dx > 0:
            self.vx = speed
        else:
            self.vx = 0
        self.vy = 0
        if self.vx != 0:
            self.set_state(EntityState.WALK)

    def distance_to(self, target: Entity) -> float:
        """Distance between collision box centers."""
        tx = getattr(target, 'col_x', target.x) + getattr(target, 'collision_width', 0) / 2
        ty = getattr(target, 'col_y', target.y) + getattr(target, 'collision_height', 0) / 2
        mx = self.col_x + self.collision_width / 2
        my = self.col_y + self.collision_height / 2
        dx = tx - mx
        dy = ty - my
        return (dx**2 + dy**2) ** 0.5

    def draw(self, surface: pygame.Surface):
        """Draw monster sprite, flipped horizontally if self.flipped. Knockup offset applied."""
        if self._fully_dead:
            return
        current_anim = self.animations.get(self.state.value)
        if not current_anim or len(current_anim) == 0:
            return
        frame = current_anim[self.current_frame_index % len(current_anim)]
        if self.flipped:
            frame = pygame.transform.flip(frame, True, False)
        # Apply fade-out alpha
        if self._fade_alpha < 255:
            frame = frame.copy()
            frame.set_alpha(self._fade_alpha)
        knockup_offset = self._status["knockup"].get("offset_y", 0)
        surface.blit(frame, (int(self.x), int(self.y + knockup_offset)))

        # HP bar above collision box
        if not self._dying:
            bar_x = int(self.col_x + self.collision_width / 2 - self._hp_bar_w / 2 + self._hp_bar_offset_x)
            bar_y = int(self.col_y + self._hp_bar_offset_y - self._hp_bar_h + knockup_offset)
            # Border (background)
            border = self._hp_border
            fill = self._hp_fill
            if self._fade_alpha < 255:
                border = border.copy()
                border.set_alpha(self._fade_alpha)
                fill = fill.copy()
                fill.set_alpha(self._fade_alpha)
            surface.blit(border, (bar_x, bar_y))
            # Fill cropped by HP ratio (inset by padding)
            hp_ratio = self.display_health / self.max_health
            fill_max_w = self._hp_bar_w - self._hp_pad_x * 2
            fill_h = self._hp_bar_h - self._hp_pad_y * 2
            if hp_ratio > 0 and fill_max_w > 0 and fill_h > 0:
                fill_w = int(fill_max_w * hp_ratio)
                surface.blit(fill, (bar_x + self._hp_pad_x, bar_y + self._hp_pad_y),
                             pygame.Rect(0, 0, fill_w, fill_h))


class Statue(Entity):
    """
    Attackable statue entity with HP bar.
    Monsters target this as their primary objective. HP = 0 → Game Over.
    """

    def __init__(self, x: float, y: float, resource_manager):
        cfg = STAT_CONFIG["statue"]
        hp_bar = cfg["hp_bar"]
        super().__init__(
            x=x, y=y,
            max_health=cfg["max_health"],
            entity_name="statue",
            animation_cache=None,
            initial_state=EntityState.IDLE
        )
        self.resource_manager = resource_manager
        self.sprite = resource_manager.get_asset("statue")

        # Target point for monsters
        self.target_offset_x = cfg["target_offset_x"]
        self.target_offset_y = cfg["target_offset_y"]
        self.collision_width = 0
        self.collision_height = 0

        # HP bar display size
        self.hp_bar_width = hp_bar["width"]
        self.hp_bar_height = hp_bar["height"]

        # Load and scale HP bar images
        hp_bar_dir = Path(__file__).parent.parent / "ingame_assets" / "ui" / "statue_hp"
        self.hp_bar_fill = pygame.image.load(str(hp_bar_dir / "HP.png")).convert_alpha()
        self.hp_bar_frame = pygame.image.load(str(hp_bar_dir / "HP_Frame.png")).convert_alpha()
        self.hp_bar_fill = pygame.transform.scale(self.hp_bar_fill, (self.hp_bar_width, self.hp_bar_height))
        self.hp_bar_frame = pygame.transform.scale(self.hp_bar_frame, (self.hp_bar_width, self.hp_bar_height))

        # Smooth HP bar display
        self.display_health = float(self.max_health)
        self._hp_lerp_speed = 60.0

    @property
    def col_x(self) -> float:
        return self.x + self.target_offset_x

    @property
    def col_y(self) -> float:
        return self.y + self.target_offset_y

    def _load_animations(self):
        pass

    def update(self, dt: float):
        if self.display_health > self.health:
            self.display_health = max(float(self.health),
                                      self.display_health - self._hp_lerp_speed * dt)

    def draw(self, surface: pygame.Surface):
        # Draw statue sprite
        if self.sprite:
            surface.blit(self.sprite, (int(self.x), int(self.y)))

        if not self.is_alive():
            return

        # HP bar position: centered above sprite
        sprite_w = self.sprite.get_width() if self.sprite else 38
        bar_x = int(self.x + sprite_w / 2 - self.hp_bar_width / 2)
        bar_y = int(self.y - self.hp_bar_height - 4)

        # Draw frame first (background)
        surface.blit(self.hp_bar_frame, (bar_x, bar_y))

        # Draw fill on top, cropped by HP ratio
        hp_ratio = self.display_health / self.max_health
        if hp_ratio > 0:
            fill_width = int(self.hp_bar_width * hp_ratio)
            surface.blit(self.hp_bar_fill, (bar_x, bar_y), pygame.Rect(0, 0, fill_width, self.hp_bar_height))


class Portal(Entity):
    """
    Animated portal that monsters spawn from.
    Customizable size. Monsters spawn from the center position.
    """

    def __init__(self, x: float, y: float, animation_cache,
                 width: int = None, height: int = None,
                 spawn_offset_x: int = None, spawn_offset_y: int = None):
        super().__init__(
            x=x, y=y,
            max_health=1,
            entity_name="portal",
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )
        # Use frame_duration from animations_config
        self.frame_duration = animation_cache.animation_durations.get("portal", {}).get("idle", 0.15)
        self._custom_width = width
        self._custom_height = height
        self.portal_width = width or self._get_frame_size()[0]
        self.portal_height = height or self._get_frame_size()[1]

        # Spawn point offset from portal top-left
        self.spawn_offset_x = spawn_offset_x if spawn_offset_x is not None else self.portal_width // 2
        self.spawn_offset_y = spawn_offset_y if spawn_offset_y is not None else self.portal_height // 2

    def _get_frame_size(self) -> tuple:
        anim = self.animations.get(self.state.value)
        if anim and len(anim) > 0:
            return anim[0].get_size()
        return (192, 192)

    def update(self, dt: float):
        self._update_animation_frame(dt)
        # Keep portal_width/height in sync if using config scale (no custom size)
        if self._custom_width is None:
            self.portal_width = self._get_frame_size()[0]
        if self._custom_height is None:
            self.portal_height = self._get_frame_size()[1]

    @property
    def center_x(self) -> float:
        return self.x + self.portal_width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.portal_height / 2

    def draw(self, surface: pygame.Surface):
        current_anim = self.animations.get(self.state.value)
        if not current_anim or len(current_anim) == 0:
            return

        frame = current_anim[self.current_frame_index % len(current_anim)]

        # Only force scale if custom width/height was explicitly set
        if self._custom_width is not None or self._custom_height is not None:
            target_w = self._custom_width or frame.get_width()
            target_h = self._custom_height or frame.get_height()
            if frame.get_width() != target_w or frame.get_height() != target_h:
                frame = pygame.transform.scale(frame, (target_w, target_h))

        surface.blit(frame, (int(self.x), int(self.y)))
