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


class EntityState(Enum):
    """Entity animation states."""
    IDLE = "idle"
    MOVE = "move"
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"


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
    
    def cast_spell(self):
        """
        Initiate spell casting.
        Transitions to CAST_SPELL animation state.
        """
        if self.mana > 0:
            self.set_state(EntityState.CAST_SPELL)
            self.mana -= 20  # Cost per spell
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
    
    def attack(self, target: Entity):
        """
        Attack a target entity.
        
        Args:
            target: Entity to attack (usually the player)
        """
        if isinstance(target, Entity):
            self.set_state(EntityState.ATTACK)
            target.take_damage(self.attack_damage)
            print(f"Monster attacks for {self.attack_damage} damage!")
    
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
