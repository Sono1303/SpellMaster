"""
Spell Logic Module - Manages spell state machine and lifecycle.

Implements a finite state machine with states: IDLE, CHANTING, ACTIVATED, EXECUTING, COOLDOWN.
All timing is frame-based and FPS-aware for consistent behavior across different hardware.
"""

from enum import Enum
import time
from config import (
    CHANT_THRESHOLD_FRAMES,
    SPELL_COOLDOWN,
    COOLDOWN_FRAMES,
    CHANT_DURATION,
    COLOR_IDLE,
    COLOR_CHANTING,
    COLOR_ACTIVATED,
    COLOR_EXECUTING,
    COLOR_COOLDOWN,
    MP_COST_PER_SPELL,
    INITIAL_HP,
    INITIAL_MP,
    MAX_HP,
    MAX_MP,
)


class SpellState(Enum):
    """Spell lifecycle states."""
    IDLE = 0          # Waiting for input
    CHANTING = 1      # Player is performing gesture
    ACTIVATED = 2     # Gesture recognized, ready to execute
    EXECUTING = 3     # Spell is executing/rendering
    COOLDOWN = 4      # Waiting for cooldown to complete


class SpellEvent(Enum):
    """Spell system events."""
    NONE = 0
    EXECUTE_SPELL = 1     # Hand released during ACTIVATED → execute spell
    CANCEL_CHANTING = 2   # Hand lost during CHANTING
    COOLDOWN_START = 3    # Cooldown started
    COOLDOWN_END = 4      # Cooldown finished


class SpellManager:
    """
    Manages spell casting state machine and lifecycle.
    
    Handles transitions between states based on frame counts and timers.
    All timing is frame-based to ensure consistency across different hardware.
    
    Benefits of frame-based timing:
    - Consistent behavior regardless of hardware performance
    - Easy to debug and reproduce issues
    - No dependency on wall-clock time (deterministic)
    """
    
    def __init__(self, fps=30, debug=False):
        """
        Initialize SpellManager.
        
        Args:
            fps: Frames per second (used for time calculations)
            debug: Enable debug logging
        """
        self.fps = fps
        self.debug = debug
        
        # Current state
        self.current_state = SpellState.IDLE
        self.previous_state = SpellState.IDLE
        
        # Frame counters
        self.frame_count = 0  # Total frames since start
        self.state_frame_count = 0  # Frames in current state
        
        # State timings (in frames, calculated from FPS)
        self.chant_threshold_frames = CHANT_THRESHOLD_FRAMES
        self.cooldown_frames = COOLDOWN_FRAMES
        
        # Spell data
        self.current_spell_name = None
        self.current_spell_confidence = 0.0
        self.spell_cast_count = 0
        
        # Timing info
        self.last_spell_time = None
        self.state_start_time = time.time()
        
        # Hand tracking (for release detection)
        self.hand_held = False
        self.hand_held_previous = False
        
        # Mana/MP system
        self.current_hp = INITIAL_HP
        self.current_mp = INITIAL_MP
        self.max_hp = MAX_HP
        self.max_mp = MAX_MP
        self.mp_cost_per_spell = MP_COST_PER_SPELL
        
        # Event system
        self.current_event = SpellEvent.NONE
        self.last_event = SpellEvent.NONE
        
        if self.debug:
            print(f"✓ SpellManager initialized (FPS: {fps})")
            print(f"  Chant threshold: {self.chant_threshold_frames} frames ({self.chant_threshold_frames/fps:.2f}s)")
            print(f"  Cooldown duration: {self.cooldown_frames} frames ({self.cooldown_frames/fps:.2f}s)")
            print(f"  HP: {self.current_hp}/{self.max_hp}, MP: {self.current_mp}/{self.max_mp}")
            print(f"  MP cost per spell: {self.mp_cost_per_spell}")
    
    def update(self):
        """
        Update spell state based on frame counter.
        
        Should be called once per frame in the main game loop.
        
        IMPORTANT: Call set_hand_held(held, spell_name) AFTER update() in the game loop
        to validate hand detection. This ensures insufficient hands trigger immediate reset.
        
        Returns:
            Current SpellState after update
        """
        self.frame_count += 1
        self.state_frame_count += 1
        
        # Clear previous event
        self.last_event = self.current_event
        self.current_event = SpellEvent.NONE
        
        # Detect hand release (transition from held to released during ACTIVATED)
        if self.current_state == SpellState.ACTIVATED and self.hand_held_previous and not self.hand_held:
            self.on_hand_released()
        
        # Update hand tracking for next frame
        self.hand_held_previous = self.hand_held
        
        # State transition logic
        if self.current_state == SpellState.IDLE:
            # IDLE → CHANTING: triggered externally via start_chanting()
            pass
        
        elif self.current_state == SpellState.CHANTING:
            # CHANTING → ACTIVATED: when threshold reached
            if self.state_frame_count >= self.chant_threshold_frames:
                self._transition_to_activated()
        
        elif self.current_state == SpellState.ACTIVATED:
            # ACTIVATED → EXECUTING: triggered externally via execute_spell()
            # Or back to IDLE if gesture is lost
            pass
        
        elif self.current_state == SpellState.EXECUTING:
            # EXECUTING → COOLDOWN: triggered externally via finish_spell()
            pass
        
        elif self.current_state == SpellState.COOLDOWN:
            # COOLDOWN → IDLE: when timer expires
            if self.state_frame_count >= self.cooldown_frames:
                self._transition_to_idle()
                self.current_event = SpellEvent.COOLDOWN_END
        
        if self.debug and self.state_frame_count % (self.fps // 2) == 0:  # Log every 0.5s
            print(f"[Frame {self.frame_count}] State: {self.current_state.name}, "
                  f"State frames: {self.state_frame_count}, Hand held: {self.hand_held}, "
                  f"MP: {self.current_mp}/{self.max_mp}")
        
        return self.current_state
    
    # ==========================================================================
    # State Transition Methods
    # ==========================================================================
    
    def start_chanting(self):
        """
        Start chanting gesture (transition to CHANTING state).
        
        Called when a hand gesture is first detected.
        """
        if self.current_state == SpellState.IDLE:
            self._change_state(SpellState.CHANTING)
            self.hand_held = True
            if self.debug:
                print(f"[Frame {self.frame_count}] → CHANTING (gesture detected)")
    
    def on_hand_released(self):
        """
        Handle hand release during ACTIVATED state.
        
        Automatically triggers spell execution if in ACTIVATED state.
        This is called automatically by update() when hand_held transitions from True to False.
        """
        if self.current_state != SpellState.ACTIVATED:
            return
        
        self.hand_held = False
        self.current_event = SpellEvent.EXECUTE_SPELL
        
        if self.debug:
            print(f"[Frame {self.frame_count}] ✓ Hand released during ACTIVATED → SpellEvent.EXECUTE_SPELL")
    
    def set_hand_held(self, held, spell_name=None):
        """
        Set hand held status with optional spell validation (call every frame from hand detection).
        
        IMPORTANT: If spell_name is None (insufficient hands detected), immediately:
        - Reset chant_timer (state_frame_count) to 0
        - Transition back to IDLE state
        
        This prevents players from "cheating" by using 1 hand to maintain a chanting state.
        
        Args:
            held: True if hand is detected, False if lost
            spell_name: The recognized spell name, or None if insufficient hands (both hands required)
        """
        self.hand_held = held
        
        # VALIDATION: If spell prediction returned None, it means MediaPipe didn't detect 2 hands
        # This requires immediate reset to prevent exploitation
        if spell_name is None and (self.current_state == SpellState.CHANTING or self.current_state == SpellState.ACTIVATED):
            # Reset chant timer and transition back to IDLE
            self.state_frame_count = 0
            old_state = self.current_state.name
            self._change_state(SpellState.IDLE)
            
            if self.debug:
                print(f"[Frame {self.frame_count}] ✗ Insufficient hands detected ({old_state} → IDLE, chant timer reset)")
    
    def validate_hand_detection(self, spell_name):
        """
        Validate hand detection and reset if needed (alternative to set_hand_held).
        
        Explicitly validates that spell recognition succeeded (requiring 2 hands).
        If spell_name is None, immediately resets CHANTING/ACTIVATED states to IDLE.
        
        This method can be called instead of set_hand_held() when you want explicit validation.
        
        Args:
            spell_name: The recognized spell name, or None if insufficient hands
        """
        if spell_name is None and (self.current_state == SpellState.CHANTING or self.current_state == SpellState.ACTIVATED):
            # Insufficient hands - reset immediately
            self.state_frame_count = 0
            old_state = self.current_state.name
            self._change_state(SpellState.IDLE)
            
            if self.debug:
                print(f"[Frame {self.frame_count}] ✗ Hand detection validation failed ({old_state} → IDLE, chant timer reset)")
    
    def _transition_to_activated(self):
        """
        Transition to ACTIVATED when chant threshold is reached.
        
        Internal method called automatically by update().
        """
        self._change_state(SpellState.ACTIVATED)
        if self.debug:
            print(f"[Frame {self.frame_count}] → ACTIVATED (chant threshold reached, "
                  f"{self.state_frame_count - 1}/{self.chant_threshold_frames} frames)")
    
    def execute_spell(self, spell_name, confidence):
        """
        Execute the recognized spell (transition to EXECUTING).
        
        Checks for sufficient mana before execution. Deducts mana cost upon success.
        
        Args:
            spell_name: Name of the spell to execute
            confidence: Confidence score (0.0-1.0)
        
        Returns:
            True if spell was executed, False if not ready or insufficient mana
        """
        if self.current_state != SpellState.ACTIVATED:
            if self.debug:
                print(f"[Frame {self.frame_count}] Cannot execute spell in {self.current_state.name} state")
            return False
        
        # Check for sufficient mana
        if self.current_mp < self.mp_cost_per_spell:
            if self.debug:
                print(f"[Frame {self.frame_count}] ✗ Insufficient mana! Need {self.mp_cost_per_spell}, "
                      f"have {self.current_mp}")
            return False
        
        # Deduct mana cost
        self.current_mp = max(0, self.current_mp - self.mp_cost_per_spell)
        
        self.current_spell_name = spell_name
        self.current_spell_confidence = confidence
        self.spell_cast_count += 1
        self.last_spell_time = time.time()
        
        self._change_state(SpellState.EXECUTING)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] → EXECUTING (spell: {spell_name}, "
                  f"confidence: {confidence*100:.1f}%, MP: {self.current_mp}/{self.max_mp})")
        
        return True
    
    def finish_spell(self, duration_frames=None):
        """
        Finish spell execution and enter cooldown (transition to COOLDOWN).
        
        Args:
            duration_frames: Custom cooldown duration in frames (None=use default)
        """
        if self.current_state != SpellState.EXECUTING:
            if self.debug:
                print(f"[Frame {self.frame_count}] Cannot finish spell in {self.current_state.name} state")
            return
        
        # Override cooldown duration if specified
        if duration_frames is not None:
            self.cooldown_frames = duration_frames
        
        self._change_state(SpellState.COOLDOWN)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] → COOLDOWN ({self.cooldown_frames} frames, "
                  f"{self.cooldown_frames/self.fps:.2f}s)")
    
    def _transition_to_idle(self):
        """
        Transition back to IDLE when cooldown expires.
        
        Internal method called automatically by update().
        """
        self._change_state(SpellState.IDLE)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] → IDLE (cooldown complete)")
    
    def cancel_chanting(self):
        """
        Cancel current chanting (return to IDLE from CHANTING state).
        
        Called when hand gesture is lost during chanting.
        """
        if self.current_state == SpellState.CHANTING:
            self._change_state(SpellState.IDLE)
            if self.debug:
                print(f"[Frame {self.frame_count}] ✗ Chanting cancelled (gesture lost)")
    
    def _change_state(self, new_state):
        """
        Change to a new state and reset frame counter.
        
        Args:
            new_state: Target SpellState
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_frame_count = 0
        self.state_start_time = time.time()
    
    # ==========================================================================
    # Query Methods
    # ==========================================================================
    
    def is_idle(self):
        """Check if in IDLE state."""
        return self.current_state == SpellState.IDLE
    
    def is_chanting(self):
        """Check if in CHANTING state."""
        return self.current_state == SpellState.CHANTING
    
    def is_activated(self):
        """Check if in ACTIVATED state."""
        return self.current_state == SpellState.ACTIVATED
    
    def is_executing(self):
        """Check if in EXECUTING state."""
        return self.current_state == SpellState.EXECUTING
    
    def is_in_cooldown(self):
        """Check if in COOLDOWN state."""
        return self.current_state == SpellState.COOLDOWN
    
    def is_ready_to_cast(self):
        """Check if ready to cast (no cooldown active)."""
        return self.current_state in (SpellState.IDLE, SpellState.CHANTING, SpellState.ACTIVATED)
    
    def has_event(self, event):
        """
        Check if a specific event occurred this frame.
        
        Args:
            event: SpellEvent to check
        
        Returns:
            True if event occurred
        """
        return self.current_event == event
    
    def get_current_event(self):
        """Get current frame's event."""
        return self.current_event
    
    def get_last_event(self):
        """Get last frame's event."""
        return self.last_event
    
    def get_chant_progress(self):
        """
        Get chanting progress as ratio (0.0 to 1.0).
        
        Returns:
            Progress ratio where 1.0 = ready to activate
        """
        if self.current_state != SpellState.CHANTING:
            return 0.0
        
        progress = self.state_frame_count / self.chant_threshold_frames
        return max(0.0, min(1.0, progress))
    
    def get_cooldown_progress(self):
        """
        Get cooldown progress as ratio (0.0 to 1.0).
        
        Returns:
            Progress ratio where 1.0 = cooldown complete
        """
        if self.current_state != SpellState.COOLDOWN:
            return 0.0
        
        progress = self.state_frame_count / self.cooldown_frames
        return max(0.0, min(1.0, progress))
    
    def get_remaining_cooldown_frames(self):
        """Get remaining cooldown frames."""
        if self.current_state != SpellState.COOLDOWN:
            return 0
        
        return max(0, self.cooldown_frames - self.state_frame_count)
    
    def get_remaining_cooldown_time(self):
        """Get remaining cooldown in seconds."""
        remaining_frames = self.get_remaining_cooldown_frames()
        return remaining_frames / self.fps
    
    # ==========================================================================
    # Mana/HP System
    # ==========================================================================
    
    def get_mp_ratio(self):
        """
        Get mana as ratio (0.0 to 1.0).
        
        Returns:
            MP ratio for UI display
        """
        if self.max_mp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_mp / self.max_mp))
    
    def get_hp_ratio(self):
        """
        Get health as ratio (0.0 to 1.0).
        
        Returns:
            HP ratio for UI display
        """
        if self.max_hp <= 0:
            return 0.0
        return max(0.0, min(1.0, self.current_hp / self.max_hp))
    
    def has_sufficient_mana(self, mana_cost=None):
        """
        Check if player has sufficient mana for spell casting.
        
        Args:
            mana_cost: Cost to check (None=default spell cost)
        
        Returns:
            True if sufficient mana available
        """
        cost = mana_cost if mana_cost is not None else self.mp_cost_per_spell
        return self.current_mp >= cost
    
    def restore_mana(self, amount):
        """
        Restore mana points.
        
        Args:
            amount: Amount to restore
        """
        old_mp = self.current_mp
        self.current_mp = min(self.max_mp, self.current_mp + amount)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] ✓ Restored {amount} MP: {old_mp} → {self.current_mp}")
    
    def take_damage(self, damage):
        """
        Reduce health from damage.
        
        Args:
            damage: Damage amount
        """
        old_hp = self.current_hp
        self.current_hp = max(0, self.current_hp - damage)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] ✗ Took {damage} damage: {old_hp} → {self.current_hp}")
    
    def heal(self, amount):
        """
        Restore health points.
        
        Args:
            amount: Amount to heal
        """
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        
        if self.debug:
            print(f"[Frame {self.frame_count}] ✓ Healed {amount} HP: {old_hp} → {self.current_hp}")
    
    # ==========================================================================
    # State Color and Display
    # ==========================================================================
    
    def get_state_color(self):
        """
        Get BGR color for current state (for UI display).
        
        Returns:
            Tuple (B, G, R) color code
        """
        state_colors = {
            SpellState.IDLE: COLOR_IDLE,
            SpellState.CHANTING: COLOR_CHANTING,
            SpellState.ACTIVATED: COLOR_ACTIVATED,
            SpellState.EXECUTING: COLOR_EXECUTING,
            SpellState.COOLDOWN: COLOR_COOLDOWN,
        }
        return state_colors.get(self.current_state, COLOR_IDLE)
    
    def get_state_name(self):
        """Get human-readable state name."""
        return self.current_state.name
    
    # ==========================================================================
    # Statistics and Debug Info
    # ==========================================================================
    
    def get_stats(self):
        """
        Get spell casting statistics as dictionary.
        
        Returns:
            Dictionary with stats info
        """
        elapsed_time = time.time() - self.state_start_time
        
        return {
            'state': self.current_state.name,
            'total_frames': self.frame_count,
            'state_frames': self.state_frame_count,
            'spell_cast_count': self.spell_cast_count,
            'current_spell': self.current_spell_name,
            'current_confidence': f"{self.current_spell_confidence*100:.1f}%",
            'state_duration_sec': f"{elapsed_time:.2f}s",
            'chant_progress': f"{self.get_chant_progress()*100:.1f}%",
            'cooldown_progress': f"{self.get_cooldown_progress()*100:.1f}%",
            'hp': f"{int(self.current_hp)}/{int(self.max_hp)}",
            'mp': f"{int(self.current_mp)}/{int(self.max_mp)}",
            'hand_held': self.hand_held,
            'event': self.current_event.name,
            'fps': self.fps,
        }
    
    def print_stats(self):
        """Print spell manager statistics to console."""
        stats = self.get_stats()
        print("\n" + "="*60)
        print("SPELL MANAGER STATISTICS")
        print("="*60)
        for key, value in stats.items():
            print(f"  {key:.<40} {value}")
        print("="*60 + "\n")
    
    def get_debug_info(self):
        """
        Get debug information for display.
        
        Returns:
            Dictionary with debug info
        """
        return {
            'State': self.current_state.name,
            'Frame': f"{self.state_frame_count}/{self._get_state_max_frames()}",
            'Spell': self.current_spell_name or "None",
            'Confidence': f"{self.current_spell_confidence*100:.0f}%" if self.current_spell_name else "0%",
            'Total Casts': self.spell_cast_count,
            'HP': f"{int(self.current_hp)}/{int(self.max_hp)}",
            'MP': f"{int(self.current_mp)}/{int(self.max_mp)}",
            'Hand Held': "✓" if self.hand_held else "✗",
            'Event': self.current_event.name,
        }
    
    def _get_state_max_frames(self):
        """Get maximum frames for current state timer."""
        if self.current_state == SpellState.CHANTING:
            return self.chant_threshold_frames
        elif self.current_state == SpellState.COOLDOWN:
            return self.cooldown_frames
        else:
            return 0
    
    def reset(self):
        """Reset spell manager to initial state."""
        self.current_state = SpellState.IDLE
        self.previous_state = SpellState.IDLE
        self.frame_count = 0
        self.state_frame_count = 0
        self.current_spell_name = None
        self.current_spell_confidence = 0.0
        self.hand_held = False
        self.hand_held_previous = False
        self.current_hp = INITIAL_HP
        self.current_mp = INITIAL_MP
        self.current_event = SpellEvent.NONE
        self.last_event = SpellEvent.NONE
        
        if self.debug:
            print(f"[Frame {self.frame_count}] SpellManager reset (HP: {self.current_hp}, MP: {self.current_mp})")
