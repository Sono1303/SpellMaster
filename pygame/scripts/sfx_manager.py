"""
SFX Manager — Loads and plays sound effects from sfx_config.json.

Reads sfx_config.json for categories (action, spell) with per-sound
volume, speed, start/end trim, and loop settings.
"""

import pygame
import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_SFX_CONFIG_PATH = _DATA_DIR / "sfx_config.json"

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _resample_sound(sound, speed):
    """Resample a Sound object to change playback speed (and pitch)."""
    if not _HAS_NUMPY or speed == 1.0:
        return sound
    try:
        arr = pygame.sndarray.array(sound)
        new_len = int(len(arr) / speed)
        if new_len < 1:
            return sound
        indices = np.linspace(0, len(arr) - 1, new_len).astype(np.int32)
        new_arr = arr[indices]
        return pygame.sndarray.make_sound(new_arr)
    except Exception as e:
        print(f"[SFX] Speed resample failed: {e}")
        return sound


class SFXManager:
    """Manages loading and playback of sound effects."""

    def __init__(self):
        self.sounds = {}  # {category: {name: {sound, end, start, loop}}}
        self._load_config()

    def _load_config(self):
        if not _SFX_CONFIG_PATH.exists():
            print(f"[SFX] Config not found: {_SFX_CONFIG_PATH}")
            return
        with open(_SFX_CONFIG_PATH, "r") as f:
            config = json.load(f)

        for category, entries in config.items():
            self.sounds[category] = {}
            for name, cfg in entries.items():
                file_path = _DATA_DIR / cfg["file"]
                if not file_path.exists():
                    print(f"[SFX] File not found: {file_path}")
                    continue
                try:
                    sound = pygame.mixer.Sound(str(file_path))
                    speed = cfg.get("speed", 1.0)
                    if speed != 1.0:
                        sound = _resample_sound(sound, speed)
                    sound.set_volume(cfg.get("volume", 1.0))
                    self.sounds[category][name] = {
                        "sound": sound,
                        "start": cfg.get("start", 0.0),
                        "end": cfg.get("end", 0.0),
                        "loop": cfg.get("loop", False),
                    }
                except Exception as e:
                    print(f"[SFX] Error loading {category}/{name}: {e}")

        total = sum(len(v) for v in self.sounds.values())
        print(f"[SFX] Loaded {total} sound effects")

    def play(self, category: str, name: str):
        """Play a sound effect. Respects end-trim and loop settings."""
        entry = self.sounds.get(category, {}).get(name)
        if not entry:
            return
        sound = entry["sound"]
        loops = -1 if entry["loop"] else 0
        maxtime = 0
        if entry["end"] > 0:
            start_ms = int(entry["start"] * 1000)
            end_ms = int(entry["end"] * 1000)
            maxtime = max(0, end_ms - start_ms)
        if maxtime > 0:
            sound.play(loops=loops, maxtime=maxtime)
        else:
            sound.play(loops=loops)

    def stop(self, category: str, name: str):
        """Stop a currently playing sound effect."""
        entry = self.sounds.get(category, {}).get(name)
        if entry:
            entry["sound"].stop()

    def stop_all(self):
        """Stop all playing sound effects."""
        for entries in self.sounds.values():
            for entry in entries.values():
                entry["sound"].stop()
