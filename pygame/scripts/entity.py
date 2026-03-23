"""
Entity Module - Spell Master Character Management
Defines base Entity class and character types (Player, Monster) with animation support.

Classes:
    Entity: Base class for all game characters with animation and health
    Player: Player-controlled wizard character
    Monster: Enemy monster character
"""

import pygame
from typing import Optional, List, Dict
from enum import Enum
from pathlib import Path


class EntityState(Enum):
    """Entity animation states."""
    IDLE = "idle"
    MOVE = "move"
    WALK_SIDE = "side_walk"
    WALK_FRONT = "front_walk"
    WALK_BACK = "back_walk"
    ATTACK = "attack"
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
        super().__init__(
            x=x,
            y=y,
            max_health=100,
            entity_name="wizard",
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )
        
        self.name = name
        self.max_mana = 100
        self.mana = self.max_mana
        self.experience = 0
        self.level = 1
        self.frame_duration = 0.15  # Wizard idle frame duration
        
        # Movement properties
        self.velocity = pygame.math.Vector2(0, 0)  # Velocity vector
        self.move_speed = 100.0  # Pixels per second

        # Collision box: offset from (self.x, self.y) and size (rectangle)
        # Adjust these to align collision with sprite visuals
        self.collision_width = 20
        self.collision_height = 35
        self.collision_offset_x = 65   # px right from sprite top-left
        self.collision_offset_y = 70   # px down from sprite top-left
        
        # Casting properties
        self.casting_stage = None  # None, "pre_cast", "casting", or "post_cast"
        self.space_pressed = False  # Track if space is currently held
        self.casting_frame_counter = 0  # Frame counter for cast animation phases
    
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
    
    def move(self, tile_map=None, dt: float = 1.0, debug: bool = False, decorations: list = None):
        """
        Move the player based on velocity, with collision detection (tiles + decorations).
        
        Performs separate X and Y collision checks for wall-sliding effect.
        If path is blocked on one axis, player can still move on the other.
        
        Args:
            tile_map: TileMap instance for collision checking
            dt: Delta time in seconds
            debug: If True, print collision debug info
            decorations: List of decoration objects with collision info
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
            if debug:
                print(f"  [X-AXIS] Checking X={next_x:.1f}, Y={self.y:.1f}")
            
            col_x = next_x + self.collision_offset_x
            col_y = self.y + self.collision_offset_y
            x_walkable, x_collision_obj = self._check_collision(
                col_x, col_y, tile_map, decorations,
                self.collision_width, self.collision_height, debug
            )

        if x_walkable:
            self.x = next_x
            if debug:
                print(f"    -> X movement ALLOWED. New X: {self.x:.1f}")
        else:
            if debug:
                collision_info = f" (blocked by '{x_collision_obj}')" if x_collision_obj else ""
                print(f"    -> X movement BLOCKED{collision_info}")

        # Try to move on Y axis (with collision check)
        if tile_map is None:
            y_walkable = True
            y_collision_obj = None
        else:
            if debug:
                print(f"  [Y-AXIS] Checking X={self.x:.1f}, Y={next_y:.1f}")

            col_x = self.x + self.collision_offset_x
            col_y = next_y + self.collision_offset_y
            y_walkable, y_collision_obj = self._check_collision(
                col_x, col_y, tile_map, decorations,
                self.collision_width, self.collision_height, debug
            )
        
        if y_walkable:
            self.y = next_y
            if debug:
                print(f"    -> Y movement ALLOWED. New Y: {self.y:.1f}")
        else:
            if debug:
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
            # Spell completes - deduct mana and show post-cast animation
            self.mana = max(0, self.mana - 0)  # Cost per spell
            self.casting_stage = "post_cast"
            self.set_state(EntityState.POST_CAST, reset_frame=True)
            print(f"{self.name} cast spell! Remaining mana: {self.mana}")
    
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
    Monster enemy character.
    
    Special properties:
    - Aggro range (detection range for combat)
    - Attack damage
    - Experience reward
    """
    
    def __init__(
        self,
        x: float,
        y: float,
        animation_cache=None,
        monster_type: str = "goblin"
    ):
        """
        Initialize a Monster.
        
        Args:
            x: Starting X position
            y: Starting Y position
            animation_cache: AnimationCache for animations
            monster_type: Type of monster (default: "goblin")
        """
        super().__init__(
            x=x,
            y=y,
            max_health=30,
            entity_name="monster",
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )
        
        self.monster_type = monster_type
        self.attack_damage = 10
        self.aggro_range = 200  # Pixels within which to detect player
        self.is_aggro = False
        self.frame_duration = 0.2  # Monster idle frame duration
        self.experience_reward = 50
        self.attack_cooldown = 1.0  # seconds between attacks
        self.attack_timer = 0.0
    
    def update(self, dt: float):
        self.attack_timer = max(0, self.attack_timer - dt)
        super().update(dt)

    def attack(self, target: Entity):
        """Attack a target entity if cooldown is ready."""
        if self.attack_timer > 0:
            return
        if isinstance(target, Entity):
            self.set_state(EntityState.ATTACK)
            target.take_damage(self.attack_damage)
            self.attack_timer = self.attack_cooldown
            print(f"Monster attacks {getattr(target, 'name', 'target')} for {self.attack_damage} damage! (HP: {target.health}/{target.max_health})")
    
    def check_aggro(self, target: Entity) -> bool:
        """
        Check if target is within aggro range.
        
        Args:
            target: Entity to check distance to
            
        Returns:
            True if within aggro range
        """
        if isinstance(target, Entity):
            dx = self.x - target.x
            dy = self.y - target.y
            distance = (dx**2 + dy**2) ** 0.5
            
            self.is_aggro = distance < self.aggro_range
            return self.is_aggro
        
        return False
    
    def move_towards(self, target: Entity, speed: float = 30.0):
        """
        Move towards a target entity.

        Args:
            target: Entity to move towards
            speed: Movement speed in pixels/second
        """
        if isinstance(target, Entity):
            dx = target.x - self.x
            dy = target.y - self.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                # Normalize direction
                norm_x = dx / distance
                norm_y = dy / distance

                # Set velocity
                self.vx = norm_x * speed
                self.vy = norm_y * speed

                self.set_state(EntityState.MOVE)


class Statue(Entity):
    """
    Attackable statue entity with HP bar.
    Monsters target this as their primary objective. HP = 0 → Game Over.
    """

    def __init__(self, x: float, y: float, resource_manager, max_health: int = 200,
                 hp_bar_width: int = 70, hp_bar_height: int = 16.8):
        super().__init__(
            x=x, y=y,
            max_health=max_health,
            entity_name="statue",
            animation_cache=None,
            initial_state=EntityState.IDLE
        )
        self.resource_manager = resource_manager
        self.sprite = resource_manager.get_asset("statue")

        # HP bar display size (customizable)
        self.hp_bar_width = hp_bar_width
        self.hp_bar_height = hp_bar_height

        # Load and scale HP bar images
        hp_bar_dir = Path(__file__).parent.parent / "ingame_assets" / "ui" / "statue_hp"
        self.hp_bar_fill = pygame.image.load(str(hp_bar_dir / "HP.png")).convert_alpha()
        self.hp_bar_frame = pygame.image.load(str(hp_bar_dir / "HP_Frame.png")).convert_alpha()
        self.hp_bar_fill = pygame.transform.scale(self.hp_bar_fill, (hp_bar_width, hp_bar_height))
        self.hp_bar_frame = pygame.transform.scale(self.hp_bar_frame, (hp_bar_width, hp_bar_height))

    def _load_animations(self):
        pass

    def update(self, dt: float):
        pass

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
        hp_ratio = self.health / self.max_health
        if hp_ratio > 0:
            fill_width = int(self.hp_bar_width * hp_ratio)
            surface.blit(self.hp_bar_fill, (bar_x, bar_y), pygame.Rect(0, 0, fill_width, self.hp_bar_height))


class Portal(Entity):
    """
    Animated portal that monsters spawn from.
    Customizable size. Monsters spawn from the center position.
    """

    def __init__(self, x: float, y: float, animation_cache,
                 width: int = None, height: int = None):
        super().__init__(
            x=x, y=y,
            max_health=1,
            entity_name="portal",
            animation_cache=animation_cache,
            initial_state=EntityState.IDLE
        )
        self.frame_duration = 0.15
        # If width/height given, force that size. Otherwise use frame size from config scale.
        self._custom_width = width
        self._custom_height = height
        self.portal_width = width or self._get_frame_size()[0]
        self.portal_height = height or self._get_frame_size()[1]

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
