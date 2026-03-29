"""
Player UI — HP and Mana container-based HUD with blink/spawn animations.

Each container represents a configurable amount of HP/Mana (default 10).
States per container: full, half, empty.
Animations: blink on gain/lose, spawn on HP gain.
"""

import pygame
import json
from pathlib import Path

_STAT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "stat_config.json"
with open(_STAT_CONFIG_PATH, "r") as _f:
    _STAT_CONFIG = json.load(_f)

_ASSETS_DIR = Path(__file__).parent.parent / "ingame_assets" / "ui" / "player_hp_mp"


def _load_img(name):
    return pygame.image.load(str(_ASSETS_DIR / name)).convert_alpha()


def _split_frames(sheet, frame_w):
    count = sheet.get_width() // frame_w
    fh = sheet.get_height()
    return [sheet.subsurface(pygame.Rect(i * frame_w, 0, frame_w, fh)).copy()
            for i in range(count)]


def _scale_img(img, scale):
    if scale == 1.0:
        return img
    return pygame.transform.scale(
        img, (int(img.get_width() * scale), int(img.get_height() * scale)))


def _scale_list(frames, scale):
    return [_scale_img(f, scale) for f in frames]


class PlayerUI:
    """Renders HP and Mana bars using sprite containers with animations."""

    _raw_hp = None  # class-level raw sprites (loaded once)
    _raw_mp = None

    def __init__(self, player):
        self.player = player
        cfg = _STAT_CONFIG.get("player_ui", {})

        # HP config
        hp_cfg = cfg.get("hp", {})
        self.hp_offset_x = hp_cfg.get("offset_x", 10)
        self.hp_offset_y = hp_cfg.get("offset_y", 10)
        self.hp_scale = hp_cfg.get("scale", 2.0)
        self.hp_spacing = hp_cfg.get("spacing", 2)
        self.hp_per = hp_cfg.get("per_container", 10)
        self.hp_blink_dur = hp_cfg.get("blink_frame_duration", 0.1)
        self.hp_blink_cycles = hp_cfg.get("blink_cycles", 2)
        self.hp_spawn_dur = hp_cfg.get("spawn_frame_duration", 0.05)

        # MP config
        mp_cfg = cfg.get("mp", {})
        self.mp_offset_x = mp_cfg.get("offset_x", 10)
        self.mp_offset_y = mp_cfg.get("offset_y", 40)
        self.mp_scale = mp_cfg.get("scale", 2.0)
        self.mp_spacing = mp_cfg.get("spacing", 2)
        self.mp_per = mp_cfg.get("per_container", 10)
        self.mp_blink_dur = mp_cfg.get("blink_frame_duration", 0.1)
        self.mp_blink_cycles = mp_cfg.get("blink_cycles", 2)

        # Load raw sprites once
        if PlayerUI._raw_hp is None:
            PlayerUI._load_raw_sprites()

        # Scale for this instance
        self._build_scaled_sprites()

        # Container counts
        self.hp_count = player.max_health // self.hp_per
        self.mp_count = int(player.max_mana) // self.mp_per

        # Track per-container state ("full", "half", "empty")
        self.hp_states = [self._cstate(player.health, self.hp_per, i)
                          for i in range(self.hp_count)]
        self.mp_states = [self._cstate(player.mana, self.mp_per, i)
                          for i in range(self.mp_count)]

        # Per-container animation: anim=None|"blink"|"spawn", timer, frame
        self.hp_anims = [{"anim": None, "timer": 0.0, "frame": 0}
                         for _ in range(self.hp_count)]
        self.mp_anims = [{"anim": None, "timer": 0.0, "frame": 0}
                         for _ in range(self.mp_count)]

    # ------------------------------------------------------------------
    # Sprite loading
    # ------------------------------------------------------------------

    @classmethod
    def _load_raw_sprites(cls):
        hp_full = _load_img("heart_normal_full.png")
        fw = hp_full.get_width()  # 16

        # Create dimmed empty heart (30% alpha)
        hp_empty = hp_full.copy()
        hp_empty.fill((255, 255, 255, 60), special_flags=pygame.BLEND_RGBA_MULT)

        cls._raw_hp = {
            "full": hp_full,
            "half": _load_img("heart_normal_half.png"),
            "empty": hp_empty,
            "blink_full": _split_frames(_load_img("heart_normal_blink_full.png"), fw),
            "blink_half": _split_frames(_load_img("heart_normal_blink_half.png"), fw),
            "spawn_full": _split_frames(_load_img("heart_normal_spawn_full.png"), fw),
            "spawn_half": _split_frames(_load_img("heart_normal_spawn_half.png"), fw),
        }

        cls._raw_mp = {
            "full": _load_img("mana_normal_full.png"),
            "half": _load_img("mana_normal_half.png"),
            "empty": _load_img("mana_empty.png"),
            "highlight": _load_img("mana_container_highlight.png"),
            "blink_full": _split_frames(_load_img("mana_normal_blink_full.png"), fw),
            "blink_half": _split_frames(_load_img("mana_normal_blink_half.png"), fw),
        }

    def _build_scaled_sprites(self):
        hs = self.hp_scale
        self.hp_spr = {
            "full": _scale_img(self._raw_hp["full"], hs),
            "half": _scale_img(self._raw_hp["half"], hs),
            "empty": _scale_img(self._raw_hp["empty"], hs),
            "blink_full": _scale_list(self._raw_hp["blink_full"], hs),
            "blink_half": _scale_list(self._raw_hp["blink_half"], hs),
            "spawn_full": _scale_list(self._raw_hp["spawn_full"], hs),
            "spawn_half": _scale_list(self._raw_hp["spawn_half"], hs),
        }
        ms = self.mp_scale
        self.mp_spr = {
            "full": _scale_img(self._raw_mp["full"], ms),
            "half": _scale_img(self._raw_mp["half"], ms),
            "empty": _scale_img(self._raw_mp["empty"], ms),
            "highlight": _scale_img(self._raw_mp["highlight"], ms),
            "blink_full": _scale_list(self._raw_mp["blink_full"], ms),
            "blink_half": _scale_list(self._raw_mp["blink_half"], ms),
        }
        self.hp_fw = self.hp_spr["full"].get_width()
        self.hp_fh = self.hp_spr["full"].get_height()
        self.mp_fw = self.mp_spr["full"].get_width()
        self.mp_fh = self.mp_spr["full"].get_height()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cstate(value, per, index):
        """Return container state: 'full', 'half', or 'empty'."""
        cv = max(0.0, min(per, value - index * per))
        if cv >= per:
            return "full"
        elif cv >= per / 2:
            return "half"
        return "empty"

    @staticmethod
    def _sval(state):
        """Numeric value of state for comparison."""
        return {"empty": 0, "half": 1, "full": 2}[state]

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt):
        p = self.player

        # Detect HP container changes
        for i in range(self.hp_count):
            new = self._cstate(p.health, self.hp_per, i)
            old = self.hp_states[i]
            if new != old:
                if self._sval(new) < self._sval(old):
                    # Lost HP: use blink_half when container empties entirely
                    btype = "half" if new == "empty" else new
                    self.hp_anims[i] = {"anim": "blink", "timer": 0.0, "frame": 0, "btype": btype}
                else:
                    self.hp_anims[i] = {"anim": "spawn", "timer": 0.0, "frame": 0}
                self.hp_states[i] = new

        # Detect MP container changes
        for i in range(self.mp_count):
            new = self._cstate(p.mana, self.mp_per, i)
            old = self.mp_states[i]
            if new != old:
                self.mp_anims[i] = {"anim": "blink", "timer": 0.0, "frame": 0}
                self.mp_states[i] = new

        # Advance HP animations
        for anim in self.hp_anims:
            if not anim["anim"]:
                continue
            anim["timer"] += dt
            if anim["anim"] == "blink":
                n_frames = len(self._raw_hp["blink_full"])
                total = n_frames * self.hp_blink_cycles
                f = int(anim["timer"] / self.hp_blink_dur)
                if f >= total:
                    anim["anim"] = None
                else:
                    anim["frame"] = f % n_frames
            elif anim["anim"] == "spawn":
                n_frames = len(self._raw_hp["spawn_full"])
                f = int(anim["timer"] / self.hp_spawn_dur)
                if f >= n_frames:
                    anim["anim"] = None
                else:
                    anim["frame"] = f

        # Advance MP animations
        for anim in self.mp_anims:
            if not anim["anim"]:
                continue
            anim["timer"] += dt
            n_frames = len(self._raw_mp["blink_full"])
            total = n_frames * self.mp_blink_cycles
            f = int(anim["timer"] / self.mp_blink_dur)
            if f >= total:
                anim["anim"] = None
            else:
                anim["frame"] = f % n_frames

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface):
        self._draw_hp(surface)
        self._draw_mp(surface)

    def _draw_hp(self, surface):
        for i in range(self.hp_count):
            x = self.hp_offset_x + i * (self.hp_fw + self.hp_spacing)
            y = self.hp_offset_y
            state = self.hp_states[i]
            anim = self.hp_anims[i]

            # Always draw empty container as background
            surface.blit(self.hp_spr["empty"], (x, y))

            if state == "empty" and not anim["anim"]:
                continue

            sprite = None
            if anim["anim"] == "blink":
                btype = anim.get("btype", state)
                frames = self.hp_spr.get(f"blink_{btype}", [])
                if frames:
                    sprite = frames[min(anim["frame"], len(frames) - 1)]
            elif anim["anim"] == "spawn":
                frames = self.hp_spr.get(f"spawn_{state}", [])
                if frames:
                    sprite = frames[min(anim["frame"], len(frames) - 1)]

            if sprite is None and state != "empty":
                sprite = self.hp_spr[state]

            if sprite:
                surface.blit(sprite, (x, y))

    def _draw_mp(self, surface):
        for i in range(self.mp_count):
            x = self.mp_offset_x + i * (self.mp_fw + self.mp_spacing)
            y = self.mp_offset_y
            state = self.mp_states[i]
            anim = self.mp_anims[i]

            # Always draw empty container as background
            surface.blit(self.mp_spr["empty"], (x, y))

            if state == "empty":
                continue

            sprite = None
            if anim["anim"] == "blink":
                frames = self.mp_spr.get(f"blink_{state}", [])
                if frames:
                    sprite = frames[min(anim["frame"], len(frames) - 1)]

            if sprite is None:
                sprite = self.mp_spr[state]

            surface.blit(sprite, (x, y))

            # Highlight overlay during blink (gain feedback)
            if anim["anim"] == "blink":
                surface.blit(self.mp_spr["highlight"], (x, y))
