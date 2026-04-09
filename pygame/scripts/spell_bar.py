"""
Spell Bar UI - Bottom-center spell icon bar with frames, highlight, and unlock system.

Icons are loaded from ingame_assets/ui/spell_icon.
Normal spells use Spell_Icon_Frame_Normal.png, crystal and phoenix use Spell_Icon_Frame_Special.png.

Special spells (unlocked_value > 0) share a kill counter. When enough kills are accumulated,
the spell unlocks. Casting it consumes kills equal to its unlocked_value.
"""

import pygame
from pathlib import Path
from spell import SPELL_NAMES, STAT_CONFIG

_ASSETS_DIR = Path(__file__).parent.parent / "ingame_assets" / "ui" / "spell_icon"

_ICON_FILES = {
    "fire": "Fire_Handsign_Fixed.jpg",
    "water": "Water_Handsign_Fixed.jpg",
    "earth": "Earth_Handsign_Fixed.jpg",
    "air": "Air_Handsign_Fixed.jpg",
    "lightning": "Lightning_Handsign_Fixed.jpg",
    "ice": "Ice_Handsign_Fixed.jpg",
    "dark": "Dark_Handsign_Fixed.jpg",
    "light": "Light_Handsign_Fixed.jpg",
    "crystal": "Crystal_Handsign_Fixed.jpg",
    "phoenix": "Phoenix_Hands_Fixedign.jpg",
}

_SPECIAL_SPELLS = {"crystal", "phoenix"}


class SpellBar:
    """Bottom-center spell icon bar with cast highlight and unlock overlay."""

    def __init__(self):
        cfg = STAT_CONFIG.get("player_ui", {}).get("spell_bar", {})
        self.icon_size = cfg.get("icon_size", 40)
        self.special_icon_size = cfg.get("special_icon_size", 52)
        self.frame_size = cfg.get("frame_size", 48)
        self.special_frame_size = cfg.get("special_frame_size", 60)
        self.spacing = cfg.get("spacing", 6)
        self.bottom_margin = cfg.get("bottom_margin", 10)
        self.highlight_scale = cfg.get("highlight_scale", 1.3)
        self.highlight_duration = cfg.get("highlight_duration", 0.3)

        self._name_font = pygame.font.Font(None, cfg.get("name_font_size", 18))
        self._warn_font = pygame.font.Font(None, 28)

        # Per-spell highlight timer
        self.highlight_timers = [0.0] * len(SPELL_NAMES)

        # Unlock system - shared kill counter
        self.shared_kills = 0
        self._prev_alive = 0  # FIX: Initialize to avoid frame 1 kill count = 0
        self.unlock_values = {}
        spell_cfgs = STAT_CONFIG.get("spells", {})
        for name in SPELL_NAMES:
            self.unlock_values[name] = spell_cfgs.get(name, {}).get("unlocked_value", 0)

        # Warning message
        self._warn_timer = 0.0
        self._warn_duration = 1.5

        # Slot sizes
        self.normal_slot = max(self.icon_size, self.frame_size)
        self.special_slot = max(self.special_icon_size, self.special_frame_size)

        # Load and scale assets
        self.icons = {}
        self.icons_highlight = {}
        self.frames = {}
        self.frames_highlight = {}

        frame_normal_raw = pygame.image.load(str(_ASSETS_DIR / "Spell_Icon_Frame_Normal.png")).convert_alpha()
        frame_special_raw = pygame.image.load(str(_ASSETS_DIR / "Spell_Icon_Frame_Special.png")).convert_alpha()

        for name in SPELL_NAMES:
            is_special = name in _SPECIAL_SPELLS
            icon_sz = self.special_icon_size if is_special else self.icon_size
            frame_sz = self.special_frame_size if is_special else self.frame_size
            hl_icon_sz = int(icon_sz * self.highlight_scale)
            hl_frame_sz = int(frame_sz * self.highlight_scale)

            raw = pygame.image.load(str(_ASSETS_DIR / _ICON_FILES[name])).convert_alpha()
            self.icons[name] = pygame.transform.smoothscale(raw, (icon_sz, icon_sz))
            self.icons_highlight[name] = pygame.transform.smoothscale(raw, (hl_icon_sz, hl_icon_sz))

            raw_frame = frame_special_raw if is_special else frame_normal_raw
            self.frames[name] = pygame.transform.smoothscale(raw_frame, (frame_sz, frame_sz))
            self.frames_highlight[name] = pygame.transform.smoothscale(raw_frame, (hl_frame_sz, hl_frame_sz))

    def _slot_size(self, name):
        return self.special_slot if name in _SPECIAL_SPELLS else self.normal_slot

    def is_locked(self, spell_index: int) -> bool:
        if 0 <= spell_index < len(SPELL_NAMES):
            name = SPELL_NAMES[spell_index]
            uv = self.unlock_values[name]
            return uv > 0 and self.shared_kills < uv
        return False

    def try_select(self, spell_index: int) -> bool:
        """Returns True if spell can be selected, False if locked (shows warning)."""
        if self.is_locked(spell_index):
            self._warn_timer = self._warn_duration
            return False
        return True

    def consume_unlock(self, spell_index: int):
        """Subtract kills when a special spell is cast."""
        if 0 <= spell_index < len(SPELL_NAMES):
            name = SPELL_NAMES[spell_index]
            uv = self.unlock_values[name]
            if uv > 0:
                print(f"[CONSUME] {name}: {self.shared_kills} -> {max(0, self.shared_kills - uv)}")
                self.shared_kills = max(0, self.shared_kills - uv)

    def add_kills(self, count: int = 1):
        self.shared_kills += count

    def trigger_highlight(self, spell_index: int):
        if 0 <= spell_index < len(self.highlight_timers):
            self.highlight_timers[spell_index] = self.highlight_duration

    def update(self, dt: float):
        for i in range(len(self.highlight_timers)):
            if self.highlight_timers[i] > 0:
                self.highlight_timers[i] = max(0.0, self.highlight_timers[i] - dt)
        if self._warn_timer > 0:
            self._warn_timer = max(0.0, self._warn_timer - dt)

    def _lock_progress(self, name: str) -> float:
        """Returns 0.0 (fully locked) to 1.0 (unlocked). Always 1.0 for unlocked_value=0."""
        uv = self.unlock_values[name]
        if uv <= 0:
            return 1.0
        return min(1.0, self.shared_kills / uv)

    def draw(self, surface: pygame.Surface, selected_index: int):
        sw = surface.get_width()
        sh = surface.get_height()

        # Calculate total bar width
        total_w = 0
        for i, name in enumerate(SPELL_NAMES):
            total_w += self._slot_size(name)
            if i < len(SPELL_NAMES) - 1:
                total_w += self.spacing

        start_x = (sw - total_w) // 2
        base_y = sh - self.bottom_margin

        x = start_x
        for i, name in enumerate(SPELL_NAMES):
            is_special = name in _SPECIAL_SPELLS
            slot = self._slot_size(name)
            icon_sz = self.special_icon_size if is_special else self.icon_size
            frame_sz = self.special_frame_size if is_special else self.frame_size
            is_selected = (i == selected_index)
            cast_highlight = self.highlight_timers[i] > 0
            progress = self._lock_progress(name)

            if is_selected or cast_highlight:
                cur_icon_sz = int(icon_sz * self.highlight_scale)
                cur_frame_sz = int(frame_sz * self.highlight_scale)
                cur_slot = int(slot * self.highlight_scale)
                icon = self.icons_highlight[name]
                frame = self.frames_highlight[name]
            else:
                cur_icon_sz = icon_sz
                cur_frame_sz = frame_sz
                cur_slot = slot
                icon = self.icons[name]
                frame = self.frames[name]

            slot_cx = x + slot // 2
            icon_x = slot_cx - cur_icon_sz // 2
            icon_y = base_y - cur_slot + (cur_slot - cur_icon_sz) // 2
            frame_x = slot_cx - cur_frame_sz // 2
            frame_y = base_y - cur_slot + (cur_slot - cur_frame_sz) // 2
            top_y = base_y - cur_slot

            # Draw icon
            surface.blit(icon, (icon_x, icon_y))

            # Draw lock overlay on icon (black, semi-transparent, covers top portion)
            if progress < 1.0:
                overlay_h = int(cur_icon_sz * (1.0 - progress))
                if overlay_h > 0:
                    overlay = pygame.Surface((cur_icon_sz, overlay_h))
                    overlay.fill((0, 0, 0))
                    overlay.set_alpha(160)
                    surface.blit(overlay, (icon_x, icon_y))

            # Draw frame on top (never covered by overlay)
            surface.blit(frame, (frame_x, frame_y))

            # Spell name above
            label = self._name_font.render(name.capitalize(), True, (255, 255, 255))
            label_x = slot_cx - label.get_width() // 2
            label_y = top_y - label.get_height() - 2
            surface.blit(label, (label_x, label_y))

            x += slot + self.spacing

        # Warning text
        if self._warn_timer > 0:
            alpha = min(255, int(255 * (self._warn_timer / self._warn_duration)))
            warn_text = self._warn_font.render("Spell is locked!", True, (255, 80, 80))
            warn_text.set_alpha(alpha)
            warn_x = sw // 2 - warn_text.get_width() // 2
            warn_y = base_y - int(self.special_slot * self.highlight_scale) - 40
            surface.blit(warn_text, (warn_x, warn_y))
