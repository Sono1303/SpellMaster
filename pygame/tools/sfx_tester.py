"""
SFX Tester — Standalone tool to preview and edit sound effects from sfx_config.json.

Usage: python sfx_tester.py

UI:
  Left panel:  Category list → SFX list
  Right:       Playback controls, waveform, editable start/end/volume
  All changes save directly to sfx_config.json
"""

import pygame
import json
import time
from pathlib import Path

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

# Paths
PYGAME_DIR = Path(__file__).parent.parent
DATA_DIR = PYGAME_DIR / "data"
SFX_CONFIG_PATH = DATA_DIR / "sfx_config.json"

# Layout
WINDOW_W, WINDOW_H = 960, 520
PANEL_W = 200
CONTENT_X = PANEL_W
CONTENT_W = WINDOW_W - PANEL_W
ITEM_H = 32
BTN_H = 36
FONT_SIZE = 18

# Colors
WHITE = (255, 255, 255)
BG_PANEL = (40, 40, 48)
BG_CONTENT = (50, 50, 58)
BG_ITEM = (55, 55, 65)
BG_ITEM_HOVER = (70, 70, 85)
BG_ITEM_SELECTED = (80, 120, 200)
TEXT_COLOR = (220, 220, 220)
TEXT_DIM = (140, 140, 150)
TEXT_VALUE = (100, 200, 255)
BTN_PLAY = (50, 160, 80)
BTN_STOP = (180, 50, 50)
BTN_HOVER_PLAY = (60, 190, 95)
BTN_HOVER_STOP = (210, 65, 65)
BTN_NEUTRAL = (80, 80, 100)
BTN_NEUTRAL_HOVER = (100, 100, 130)
BAR_BG = (30, 30, 36)
BAR_FILL = (60, 140, 220)
BAR_REGION = (80, 200, 120)
BAR_CURSOR = (255, 80, 80)


def load_config():
    with open(SFX_CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(data):
    with open(SFX_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


class SfxTester:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100)
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("SFX Tester")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", FONT_SIZE)
        self.font_sm = pygame.font.SysFont("Consolas", 14)
        self.font_lg = pygame.font.SysFont("Consolas", 22)

        self.config = load_config()
        self.categories = list(self.config.keys())
        self.selected_cat = 0
        self.selected_sfx = 0
        self.sfx_names = []
        self._rebuild_sfx_list()

        # Audio state
        self.sound: pygame.mixer.Sound = None
        self.sound_length = 0.0  # total duration in seconds
        self.channel: pygame.mixer.Channel = None
        self.playing = False
        self.play_start_time = 0.0  # time.time() when playback started
        self.play_offset = 0.0     # start offset in seconds

        # Current config values (editable)
        self.cur_volume = 1.0
        self.cur_speed = 1.0
        self.cur_start = 0.0
        self.cur_end = 0.0

        # Scroll
        self.cat_scroll = 0
        self.sfx_scroll = 0

        # Dragging state for progress bar
        self._dragging_bar = False

        self._load_selected_sfx()

    def _rebuild_sfx_list(self):
        if not self.categories:
            self.sfx_names = []
            return
        cat = self.categories[self.selected_cat]
        self.sfx_names = list(self.config.get(cat, {}).keys())
        self.selected_sfx = min(self.selected_sfx, max(len(self.sfx_names) - 1, 0))
        self.sfx_scroll = 0

    def _get_current_cfg(self):
        if not self.categories or not self.sfx_names:
            return None
        cat = self.categories[self.selected_cat]
        sfx = self.sfx_names[self.selected_sfx]
        return self.config[cat][sfx]

    def _load_selected_sfx(self):
        self._stop_playback()
        self.sound = None
        self.sound_length = 0.0
        cfg = self._get_current_cfg()
        if not cfg:
            return
        file_rel = cfg.get("file", "")
        file_path = DATA_DIR / file_rel
        if not file_path.exists():
            print(f"[WARN] SFX not found: {file_path}")
            return
        try:
            self.sound = pygame.mixer.Sound(str(file_path))
            self.sound_length = self.sound.get_length()
            self.cur_volume = cfg.get("volume", 1.0)
            self.cur_speed = cfg.get("speed", 1.0)
            self.cur_start = cfg.get("start", 0.0)
            self.cur_end = cfg.get("end", 0.0)
            self.sound.set_volume(self.cur_volume)
            cat = self.categories[self.selected_cat]
            sfx = self.sfx_names[self.selected_sfx]
            print(f"[OK] Loaded {cat}/{sfx}: {self.sound_length:.2f}s")
        except Exception as e:
            print(f"[ERR] Failed to load SFX: {e}")

    def _play_from_start(self):
        if not self.sound:
            return
        self._stop_playback()
        play_sound = self.sound
        # Apply speed via resampling
        if _HAS_NUMPY and self.cur_speed != 1.0:
            try:
                arr = pygame.sndarray.array(self.sound)
                new_len = int(len(arr) / self.cur_speed)
                if new_len > 0:
                    indices = np.linspace(0, len(arr) - 1, new_len).astype(np.int32)
                    play_sound = pygame.sndarray.make_sound(arr[indices])
            except Exception:
                pass
        play_sound.set_volume(self.cur_volume)
        # Calculate effective start/end
        end_sec = self.cur_end if self.cur_end > 0 else self.sound_length
        duration_ms = max(0, int((end_sec - self.cur_start) * 1000 / self.cur_speed))
        if duration_ms <= 0:
            return
        self.channel = play_sound.play(maxtime=duration_ms, fade_ms=0)
        self._play_sound_ref = play_sound  # prevent GC
        self.playing = True
        self.play_start_time = time.time()
        self.play_offset = self.cur_start

    def _stop_playback(self):
        if self.channel and self.channel.get_busy():
            self.channel.stop()
        self.playing = False

    def _get_playback_pos(self):
        """Current playback position in seconds."""
        if not self.playing:
            return self.play_offset
        elapsed = time.time() - self.play_start_time
        pos = self.play_offset + elapsed
        end = self.cur_end if self.cur_end > 0 else self.sound_length
        if pos >= end:
            self.playing = False
            return end
        return pos

    def _save_current(self):
        """Save current sfx config values to file."""
        cfg = self._get_current_cfg()
        if not cfg:
            return
        cfg["volume"] = round(self.cur_volume, 2)
        cfg["speed"] = round(self.cur_speed, 2)
        cfg["start"] = round(self.cur_start, 2)
        cfg["end"] = round(self.cur_end, 2)
        save_config(self.config)
        cat = self.categories[self.selected_cat]
        sfx = self.sfx_names[self.selected_sfx]
        print(f"[SAVED] {cat}/{sfx}: vol={self.cur_volume:.2f} speed={self.cur_speed:.2f} start={self.cur_start:.2f} end={self.cur_end:.2f}")

    def _reload_config(self):
        old_cat = self.categories[self.selected_cat] if self.categories else None
        old_sfx = self.sfx_names[self.selected_sfx] if self.sfx_names else None
        self.config = load_config()
        self.categories = list(self.config.keys())
        if old_cat in self.categories:
            self.selected_cat = self.categories.index(old_cat)
        else:
            self.selected_cat = 0
        self._rebuild_sfx_list()
        if old_sfx in self.sfx_names:
            self.selected_sfx = self.sfx_names.index(old_sfx)
        self._load_selected_sfx()
        print("[OK] Config reloaded")

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F5:
                        self._reload_config()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_click(event.pos, event.button)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._dragging_bar = False
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_scroll(event.y)

            # Check if playback ended
            if self.playing and self.channel and not self.channel.get_busy():
                self.playing = False

            # Drag on progress bar
            if self._dragging_bar:
                mx, _ = pygame.mouse.get_pos()
                self._seek_from_bar(mx)

            self._draw()
            pygame.display.flip()

        pygame.quit()

    def _handle_scroll(self, scroll_y):
        mx, my = pygame.mouse.get_pos()
        if mx < PANEL_W:
            cat_section_h = min(len(self.categories) * ITEM_H + ITEM_H, WINDOW_H // 2)
            if my < cat_section_h:
                self.cat_scroll = max(0, self.cat_scroll - scroll_y * ITEM_H)
            else:
                self.sfx_scroll = max(0, self.sfx_scroll - scroll_y * ITEM_H)

    def _handle_click(self, pos, button):
        mx, my = pos

        # Left panel
        if mx < PANEL_W:
            cat_section_h = min(len(self.categories) * ITEM_H + ITEM_H, WINDOW_H // 2)
            if ITEM_H <= my < cat_section_h:
                idx = (my - ITEM_H + self.cat_scroll) // ITEM_H
                if 0 <= idx < len(self.categories):
                    self.selected_cat = idx
                    self.selected_sfx = 0
                    self._rebuild_sfx_list()
                    self._load_selected_sfx()
                return

            sfx_y_start = cat_section_h + ITEM_H
            if my >= sfx_y_start:
                idx = (my - sfx_y_start + self.sfx_scroll) // ITEM_H
                if 0 <= idx < len(self.sfx_names):
                    self.selected_sfx = idx
                    self._load_selected_sfx()
            return

        # Right panel buttons
        btn_y = 20
        # Play button
        if pygame.Rect(CONTENT_X + 20, btn_y, 100, BTN_H).collidepoint(mx, my):
            self._play_from_start()
            return
        # Stop button
        if pygame.Rect(CONTENT_X + 140, btn_y, 100, BTN_H).collidepoint(mx, my):
            self._stop_playback()
            return

        # Progress bar click
        bar_rect = self._get_bar_rect()
        if bar_rect.collidepoint(mx, my):
            self._dragging_bar = True
            self._seek_from_bar(mx)
            return

        # Volume controls
        vol_y = 140
        if pygame.Rect(CONTENT_X + 130, vol_y, 36, BTN_H).collidepoint(mx, my):
            self.cur_volume = round(max(0.0, self.cur_volume - 0.05), 2)
            if self.sound:
                self.sound.set_volume(self.cur_volume)
            self._save_current()
            return
        if pygame.Rect(CONTENT_X + 330, vol_y, 36, BTN_H).collidepoint(mx, my):
            self.cur_volume = round(min(1.0, self.cur_volume + 0.05), 2)
            if self.sound:
                self.sound.set_volume(self.cur_volume)
            self._save_current()
            return

        # Speed controls
        speed_y = 190
        if pygame.Rect(CONTENT_X + 130, speed_y, 36, BTN_H).collidepoint(mx, my):
            self.cur_speed = round(max(0.25, self.cur_speed - 0.05), 2)
            self._save_current()
            return
        if pygame.Rect(CONTENT_X + 330, speed_y, 36, BTN_H).collidepoint(mx, my):
            self.cur_speed = round(min(3.0, self.cur_speed + 0.05), 2)
            self._save_current()
            return

        # Start controls
        start_y = 240
        if pygame.Rect(CONTENT_X + 130, start_y, 36, BTN_H).collidepoint(mx, my):
            self.cur_start = round(max(0.0, self.cur_start - 0.1), 2)
            self._save_current()
            return
        if pygame.Rect(CONTENT_X + 330, start_y, 36, BTN_H).collidepoint(mx, my):
            max_start = (self.cur_end if self.cur_end > 0 else self.sound_length) - 0.1
            self.cur_start = round(min(max_start, self.cur_start + 0.1), 2)
            self._save_current()
            return

        # End controls
        end_y = 290
        if pygame.Rect(CONTENT_X + 130, end_y, 36, BTN_H).collidepoint(mx, my):
            new_end = round(self.cur_end - 0.1, 2)
            if new_end <= self.cur_start:
                new_end = 0.0  # 0 = full length
            self.cur_end = max(0.0, new_end)
            self._save_current()
            return
        if pygame.Rect(CONTENT_X + 330, end_y, 36, BTN_H).collidepoint(mx, my):
            if self.cur_end == 0.0:
                self.cur_end = round(self.cur_start + 0.1, 2)
            else:
                self.cur_end = round(min(self.sound_length, self.cur_end + 0.1), 2)
            self._save_current()
            return

        # Loop toggle
        loop_y = 340
        if pygame.Rect(CONTENT_X + 130, loop_y, 100, BTN_H).collidepoint(mx, my):
            cfg = self._get_current_cfg()
            if cfg:
                cfg["loop"] = not cfg.get("loop", False)
                save_config(self.config)
            return

    def _get_bar_rect(self):
        return pygame.Rect(CONTENT_X + 20, 80, CONTENT_W - 40, 30)

    def _seek_from_bar(self, mouse_x):
        bar = self._get_bar_rect()
        ratio = max(0.0, min(1.0, (mouse_x - bar.x) / bar.width))
        pos = ratio * self.sound_length
        self.play_offset = pos
        self.play_start_time = time.time()

    def _draw(self):
        self.screen.fill(BG_PANEL)
        mouse_pos = pygame.mouse.get_pos()

        # === LEFT PANEL ===
        # Category list
        self._draw_header(0, "Categories (F5)")
        cat_section_h = min(len(self.categories) * ITEM_H + ITEM_H, WINDOW_H // 2)
        clip = pygame.Rect(0, ITEM_H, PANEL_W, cat_section_h - ITEM_H)
        self.screen.set_clip(clip)
        for i, name in enumerate(self.categories):
            y = ITEM_H + i * ITEM_H - self.cat_scroll
            self._draw_list_item(0, y, PANEL_W, name, i == self.selected_cat, mouse_pos)
        self.screen.set_clip(None)

        # SFX list
        sfx_header_y = cat_section_h
        self._draw_header(sfx_header_y, "Sounds")
        sfx_y_start = sfx_header_y + ITEM_H
        clip2 = pygame.Rect(0, sfx_y_start, PANEL_W, WINDOW_H - sfx_y_start)
        self.screen.set_clip(clip2)
        for i, name in enumerate(self.sfx_names):
            y = sfx_y_start + i * ITEM_H - self.sfx_scroll
            self._draw_list_item(0, y, PANEL_W, name, i == self.selected_sfx, mouse_pos)
        self.screen.set_clip(None)

        # Separator
        pygame.draw.line(self.screen, (80, 80, 90), (PANEL_W, 0), (PANEL_W, WINDOW_H), 2)

        # === RIGHT PANEL ===
        # Play / Stop
        btn_y = 20
        self._draw_button(CONTENT_X + 20, btn_y, 100, BTN_H,
                          "Play", BTN_PLAY, BTN_HOVER_PLAY, mouse_pos)
        self._draw_button(CONTENT_X + 140, btn_y, 100, BTN_H,
                          "Stop", BTN_STOP, BTN_HOVER_STOP, mouse_pos)

        # Status
        status = "Playing" if self.playing else "Stopped"
        self.screen.blit(self.font_sm.render(status, True, TEXT_DIM),
                         (CONTENT_X + 260, btn_y + 10))

        # File info
        if self.sound:
            info = f"Length: {self.sound_length:.2f}s"
            self.screen.blit(self.font_sm.render(info, True, TEXT_DIM),
                             (CONTENT_X + 260, btn_y + 26))

        # === PROGRESS BAR ===
        bar = self._get_bar_rect()
        pygame.draw.rect(self.screen, BAR_BG, bar, border_radius=4)

        if self.sound_length > 0:
            # Draw start/end region highlight
            eff_end = self.cur_end if self.cur_end > 0 else self.sound_length
            rx1 = bar.x + int(bar.width * self.cur_start / self.sound_length)
            rx2 = bar.x + int(bar.width * eff_end / self.sound_length)
            region = pygame.Rect(rx1, bar.y, max(rx2 - rx1, 1), bar.height)
            region_surf = pygame.Surface((region.width, region.height))
            region_surf.fill(BAR_REGION)
            region_surf.set_alpha(60)
            self.screen.blit(region_surf, region.topleft)

            # Playback cursor
            pos = self._get_playback_pos()
            cursor_x = bar.x + int(bar.width * pos / self.sound_length)
            pygame.draw.line(self.screen, BAR_CURSOR,
                             (cursor_x, bar.y), (cursor_x, bar.y + bar.height), 2)

            # Time label
            pos_text = f"{pos:.2f}s / {self.sound_length:.2f}s"
            self.screen.blit(self.font_sm.render(pos_text, True, TEXT_DIM),
                             (bar.x, bar.y + bar.height + 4))

            # Start/End markers text
            start_text = f"S:{self.cur_start:.2f}"
            end_text = f"E:{eff_end:.2f}"
            self.screen.blit(self.font_sm.render(start_text, True, BAR_REGION),
                             (rx1, bar.y - 16))
            end_surf = self.font_sm.render(end_text, True, BAR_REGION)
            self.screen.blit(end_surf, (rx2 - end_surf.get_width(), bar.y - 16))

        # === EDITABLE PARAMETERS ===
        param_x = CONTENT_X + 20

        # Volume
        vol_y = 140
        self._draw_param_row(param_x, vol_y, "Volume", f"{self.cur_volume:.2f}", mouse_pos)

        # Speed
        speed_y = 190
        self._draw_param_row(param_x, speed_y, "Speed", f"{self.cur_speed:.2f}x", mouse_pos)

        # Start
        start_y = 240
        self._draw_param_row(param_x, start_y, "Start (s)", f"{self.cur_start:.2f}", mouse_pos)

        # End
        end_y = 290
        end_display = f"{self.cur_end:.2f}" if self.cur_end > 0 else f"0 (full)"
        self._draw_param_row(param_x, end_y, "End (s)", end_display, mouse_pos)

        # Loop toggle
        loop_y = 340
        cfg = self._get_current_cfg()
        loop_val = cfg.get("loop", False) if cfg else False
        self.screen.blit(self.font.render("Loop", True, TEXT_COLOR), (param_x, loop_y + 8))
        loop_color = BTN_PLAY if loop_val else BTN_NEUTRAL
        loop_hover = BTN_HOVER_PLAY if loop_val else BTN_NEUTRAL_HOVER
        loop_text = "ON" if loop_val else "OFF"
        self._draw_button(CONTENT_X + 130, loop_y, 100, BTN_H,
                          loop_text, loop_color, loop_hover, mouse_pos)

    def _draw_param_row(self, x, y, label, value_text, mouse_pos):
        """Draw: Label   [-]  value  [+]"""
        self.screen.blit(self.font.render(label, True, TEXT_COLOR), (x, y + 8))
        self._draw_button(CONTENT_X + 130, y, 36, BTN_H,
                          "-", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, mouse_pos)
        val_surf = self.font.render(value_text, True, TEXT_VALUE)
        val_x = CONTENT_X + 180 + (140 - val_surf.get_width()) // 2
        self.screen.blit(val_surf, (val_x, y + (BTN_H - val_surf.get_height()) // 2))
        self._draw_button(CONTENT_X + 330, y, 36, BTN_H,
                          "+", BTN_NEUTRAL, BTN_NEUTRAL_HOVER, mouse_pos)

    def _draw_header(self, y, text):
        rect = pygame.Rect(0, y, PANEL_W, ITEM_H)
        pygame.draw.rect(self.screen, (30, 30, 36), rect)
        surf = self.font.render(text, True, (180, 180, 200))
        self.screen.blit(surf, (8, y + (ITEM_H - surf.get_height()) // 2))

    def _draw_list_item(self, x, y, w, text, selected, mouse_pos):
        rect = pygame.Rect(x + 2, y + 1, w - 4, ITEM_H - 2)
        hovered = rect.collidepoint(mouse_pos)
        if selected:
            color = BG_ITEM_SELECTED
        elif hovered:
            color = BG_ITEM_HOVER
        else:
            color = BG_ITEM
        pygame.draw.rect(self.screen, color, rect, border_radius=4)
        surf = self.font.render(text, True, TEXT_COLOR)
        self.screen.blit(surf, (x + 10, y + (ITEM_H - surf.get_height()) // 2))

    def _draw_button(self, x, y, w, h, text, color, hover_color, mouse_pos):
        rect = pygame.Rect(x, y, w, h)
        hovered = rect.collidepoint(mouse_pos)
        pygame.draw.rect(self.screen, hover_color if hovered else color, rect, border_radius=6)
        surf = self.font.render(text, True, WHITE)
        self.screen.blit(surf, (x + (w - surf.get_width()) // 2,
                                y + (h - surf.get_height()) // 2))


if __name__ == "__main__":
    tester = SfxTester()
    tester.run()
