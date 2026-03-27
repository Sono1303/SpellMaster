"""
Animation Tester — Standalone tool to preview animations from animations_config.json.

Usage: python animation_tester.py

UI:
  Left panel:  Entity/Spell list → Animation list
  Center:      Animation preview (white background)
  Bottom:      Play / Stop buttons, frame info
"""

import pygame
import json
import sys
from pathlib import Path

# Paths
PYGAME_DIR = Path(__file__).parent.parent
DATA_DIR = PYGAME_DIR / "data"
ANIM_CONFIG_PATH = DATA_DIR / "animations_config.json"

# Layout constants
WINDOW_W, WINDOW_H = 960, 640
PANEL_W = 200
PREVIEW_X = PANEL_W
PREVIEW_W = WINDOW_W - PANEL_W
ITEM_H = 32
BTN_H = 36
FONT_SIZE = 18

# Colors
WHITE = (255, 255, 255)
BG_PANEL = (40, 40, 48)
BG_ITEM = (55, 55, 65)
BG_ITEM_HOVER = (70, 70, 85)
BG_ITEM_SELECTED = (80, 120, 200)
TEXT_COLOR = (220, 220, 220)
TEXT_DIM = (140, 140, 150)
BTN_PLAY = (50, 160, 80)
BTN_STOP = (180, 50, 50)
BTN_HOVER_PLAY = (60, 190, 95)
BTN_HOVER_STOP = (210, 65, 65)
GRID_LINE = (230, 230, 230)


def load_config():
    with open(ANIM_CONFIG_PATH, "r") as f:
        return json.load(f).get("animations", {})


def extract_frames(sheet_path, cfg):
    """Extract and scale frames from a sprite sheet using grid config."""
    sheet = pygame.image.load(str(sheet_path)).convert_alpha()
    grid_rows = cfg.get("grid_rows", 1)
    grid_cols = cfg.get("grid_cols", 1)
    start_row = cfg.get("start_row", 0)
    start_col = cfg.get("start_col", 0)
    frame_count = cfg.get("frame_count", 1)
    scale = cfg.get("scale", 1.0)

    fw = sheet.get_width() // grid_cols
    fh = sheet.get_height() // grid_rows
    if fw == 0 or fh == 0:
        return [], 0, 0

    frames = []
    for i in range(frame_count):
        linear = start_col + i
        row = start_row + linear // grid_cols
        col = linear % grid_cols
        rect = pygame.Rect(col * fw, row * fh, fw, fh)
        frame = sheet.subsurface(rect).copy()
        if scale != 1.0:
            frame = pygame.transform.scale(
                frame, (int(fw * scale), int(fh * scale)))
        frames.append(frame)

    scaled_w = int(fw * scale) if frames else 0
    scaled_h = int(fh * scale) if frames else 0
    return frames, scaled_w, scaled_h


class AnimationTester:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Animation Tester")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Consolas", FONT_SIZE)
        self.font_sm = pygame.font.SysFont("Consolas", 14)

        self.config = load_config()
        self.entity_names = list(self.config.keys())
        self.selected_entity = 0
        self.selected_anim = 0
        self.anim_names = []
        self._rebuild_anim_list()

        # Playback state
        self.frames = []
        self.frame_w = 0
        self.frame_h = 0
        self.frame_duration = 0.15
        self.current_frame = 0
        self.elapsed = 0.0
        self.playing = False

        # Scroll offsets
        self.entity_scroll = 0
        self.anim_scroll = 0

        # Scale
        self.cur_scale = 1.0

        # Load initial
        self._load_selected_animation()

    def _rebuild_anim_list(self):
        if not self.entity_names:
            self.anim_names = []
            return
        entity = self.entity_names[self.selected_entity]
        self.anim_names = list(self.config.get(entity, {}).keys())
        self.selected_anim = min(self.selected_anim, max(len(self.anim_names) - 1, 0))
        self.anim_scroll = 0

    def _load_selected_animation(self):
        self.frames = []
        self.current_frame = 0
        self.elapsed = 0.0
        if not self.entity_names or not self.anim_names:
            return
        entity = self.entity_names[self.selected_entity]
        anim = self.anim_names[self.selected_anim]
        cfg = self.config[entity][anim]
        sheet_rel = cfg.get("sprite_sheet", "")
        sheet_path = DATA_DIR / sheet_rel
        if not sheet_path.exists():
            print(f"[WARN] Sprite sheet not found: {sheet_path}")
            return
        self.frames, self.frame_w, self.frame_h = extract_frames(sheet_path, cfg)
        self.frame_duration = cfg.get("frame_duration", 0.15)
        self.cur_scale = cfg.get("scale", 1.0)
        print(f"[OK] Loaded {entity}/{anim}: {len(self.frames)} frames, "
              f"{self.frame_w}x{self.frame_h}px, scale={self.cur_scale}, dur={self.frame_duration}s")

    def _reload_config(self):
        """Hot-reload config from disk."""
        old_entity = self.entity_names[self.selected_entity] if self.entity_names else None
        old_anim = self.anim_names[self.selected_anim] if self.anim_names else None
        self.config = load_config()
        self.entity_names = list(self.config.keys())
        # Restore selection
        if old_entity in self.entity_names:
            self.selected_entity = self.entity_names.index(old_entity)
        else:
            self.selected_entity = 0
        self._rebuild_anim_list()
        if old_anim in self.anim_names:
            self.selected_anim = self.anim_names.index(old_anim)
        self._load_selected_animation()
        print("[OK] Config reloaded")

    def _save_config_value(self, key, value):
        """Write a value back to animations_config.json for current selection."""
        if not self.entity_names or not self.anim_names:
            return
        entity = self.entity_names[self.selected_entity]
        anim = self.anim_names[self.selected_anim]
        with open(ANIM_CONFIG_PATH, "r") as f:
            full_data = json.load(f)
        full_data["animations"][entity][anim][key] = value
        with open(ANIM_CONFIG_PATH, "w") as f:
            json.dump(full_data, f, indent=2)
        self.config[entity][anim][key] = value
        print(f"[SAVED] {entity}/{anim} {key} = {value}")

    def _save_frame_duration(self):
        self._save_config_value("frame_duration", round(self.frame_duration, 3))

    def _save_scale(self):
        self._save_config_value("scale", round(self.cur_scale, 1))
        self._load_selected_animation()  # reload frames with new scale

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
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_scroll(event.y)

            # Update animation
            if self.playing and self.frames:
                self.elapsed += dt
                if self.elapsed >= self.frame_duration:
                    self.elapsed -= self.frame_duration
                    self.current_frame = (self.current_frame + 1) % len(self.frames)

            self._draw()
            pygame.display.flip()

        pygame.quit()

    def _handle_scroll(self, scroll_y):
        mx, _ = pygame.mouse.get_pos()
        if mx < PANEL_W:
            # Determine which list the mouse is over
            _, my = pygame.mouse.get_pos()
            entity_list_h = len(self.entity_names) * ITEM_H
            if my < min(entity_list_h + ITEM_H, WINDOW_H // 2):
                self.entity_scroll = max(0, self.entity_scroll - scroll_y * ITEM_H)
            else:
                self.anim_scroll = max(0, self.anim_scroll - scroll_y * ITEM_H)

    def _handle_click(self, pos, button):
        mx, my = pos

        # Left panel — entity list
        if mx < PANEL_W:
            # Header "Entities" is at y=0, items start at ITEM_H
            entity_section_h = min(len(self.entity_names) * ITEM_H + ITEM_H, WINDOW_H // 2)

            if ITEM_H <= my < entity_section_h:
                idx = (my - ITEM_H + self.entity_scroll) // ITEM_H
                if 0 <= idx < len(self.entity_names):
                    self.selected_entity = idx
                    self.selected_anim = 0
                    self._rebuild_anim_list()
                    self._load_selected_animation()
                    self.playing = False
                return

            # Anim list starts after entity section
            anim_y_start = entity_section_h + ITEM_H  # +ITEM_H for "Animations" header
            if my >= anim_y_start:
                idx = (my - anim_y_start + self.anim_scroll) // ITEM_H
                if 0 <= idx < len(self.anim_names):
                    self.selected_anim = idx
                    self._load_selected_animation()
                    self.playing = False
            return

        # Buttons at bottom of preview area
        btn_y = WINDOW_H - BTN_H - 10
        btn_play_rect = pygame.Rect(PREVIEW_X + 20, btn_y, 100, BTN_H)
        btn_stop_rect = pygame.Rect(PREVIEW_X + 140, btn_y, 100, BTN_H)

        if btn_play_rect.collidepoint(mx, my):
            if self.frames:
                self.playing = True
                if self.current_frame >= len(self.frames) - 1:
                    self.current_frame = 0
                    self.elapsed = 0.0
        elif btn_stop_rect.collidepoint(mx, my):
            self.playing = False

    def _draw(self):
        self.screen.fill(BG_PANEL)

        # === LEFT PANEL ===
        panel_rect = pygame.Rect(0, 0, PANEL_W, WINDOW_H)
        pygame.draw.rect(self.screen, BG_PANEL, panel_rect)

        mouse_pos = pygame.mouse.get_pos()

        # Entity list
        self._draw_header(0, "Entities (F5 reload)")
        entity_section_h = min(len(self.entity_names) * ITEM_H + ITEM_H, WINDOW_H // 2)
        clip = pygame.Rect(0, ITEM_H, PANEL_W, entity_section_h - ITEM_H)
        self.screen.set_clip(clip)
        for i, name in enumerate(self.entity_names):
            y = ITEM_H + i * ITEM_H - self.entity_scroll
            selected = (i == self.selected_entity)
            self._draw_list_item(0, y, PANEL_W, name, selected, mouse_pos)
        self.screen.set_clip(None)

        # Anim list
        anim_header_y = entity_section_h
        self._draw_header(anim_header_y, "Animations")
        anim_y_start = anim_header_y + ITEM_H
        clip2 = pygame.Rect(0, anim_y_start, PANEL_W, WINDOW_H - anim_y_start)
        self.screen.set_clip(clip2)
        for i, name in enumerate(self.anim_names):
            y = anim_y_start + i * ITEM_H - self.anim_scroll
            selected = (i == self.selected_anim)
            self._draw_list_item(0, y, PANEL_W, name, selected, mouse_pos)
        self.screen.set_clip(None)

        # Separator line
        pygame.draw.line(self.screen, (80, 80, 90), (PANEL_W, 0), (PANEL_W, WINDOW_H), 2)

        # === PREVIEW AREA ===
        preview_rect = pygame.Rect(PREVIEW_X, 0, PREVIEW_W, WINDOW_H - BTN_H - 30)
        pygame.draw.rect(self.screen, WHITE, preview_rect)

        if self.frames:
            frame = self.frames[self.current_frame % len(self.frames)]
            # Center in preview area
            cx = PREVIEW_X + PREVIEW_W // 2 - frame.get_width() // 2
            cy = (WINDOW_H - BTN_H - 30) // 2 - frame.get_height() // 2
            self.screen.blit(frame, (cx, cy))


        # === INFO BAR ===
        info_y = WINDOW_H - BTN_H - 28
        info_bg = pygame.Rect(PREVIEW_X, info_y, PREVIEW_W, 20)
        pygame.draw.rect(self.screen, BG_PANEL, info_bg)
        if self.frames:
            info = (f"Frame: {self.current_frame + 1}/{len(self.frames)}  |  "
                    f"Size: {self.frame_w}x{self.frame_h}  |  "
                    f"Duration: {self.frame_duration}s  |  "
                    f"{'Playing' if self.playing else 'Stopped'}")
        else:
            info = "No animation loaded"
        self.screen.blit(self.font_sm.render(info, True, TEXT_DIM),
                         (PREVIEW_X + 10, info_y + 2))

        # === BUTTONS ===
        btn_y = WINDOW_H - BTN_H - 6
        self._draw_button(PREVIEW_X + 20, btn_y, 100, BTN_H,
                          "Play", BTN_PLAY, BTN_HOVER_PLAY, mouse_pos)
        self._draw_button(PREVIEW_X + 140, btn_y, 100, BTN_H,
                          "Stop", BTN_STOP, BTN_HOVER_STOP, mouse_pos)

        # Step buttons (< >)
        self._draw_button(PREVIEW_X + 260, btn_y, 50, BTN_H,
                          "<", (80, 80, 100), (100, 100, 130), mouse_pos)
        self._draw_button(PREVIEW_X + 320, btn_y, 50, BTN_H,
                          ">", (80, 80, 100), (100, 100, 130), mouse_pos)

        # Speed controls: [-] value [+]
        speed_color = (80, 80, 100)
        speed_hover = (100, 100, 130)
        self._draw_button(PREVIEW_X + 390, btn_y, 36, BTN_H,
                          "-", speed_color, speed_hover, mouse_pos)
        speed_text = f"{self.frame_duration:.3f}s"
        speed_surf = self.font.render(speed_text, True, TEXT_DIM)
        self.screen.blit(speed_surf, (PREVIEW_X + 434, btn_y + (BTN_H - speed_surf.get_height()) // 2))
        self._draw_button(PREVIEW_X + 520, btn_y, 36, BTN_H,
                          "+", speed_color, speed_hover, mouse_pos)

        # Scale controls: [-] value [+]
        self._draw_button(PREVIEW_X + 580, btn_y, 36, BTN_H,
                          "-", speed_color, speed_hover, mouse_pos)
        scale_text = f"x{self.cur_scale:.1f}"
        scale_surf = self.font.render(scale_text, True, TEXT_DIM)
        self.screen.blit(scale_surf, (PREVIEW_X + 624, btn_y + (BTN_H - scale_surf.get_height()) // 2))
        self._draw_button(PREVIEW_X + 700, btn_y, 36, BTN_H,
                          "+", speed_color, speed_hover, mouse_pos)

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

        # Handle step button clicks in _handle_click
        # (handled separately below)

    def _handle_click(self, pos, button):
        mx, my = pos

        # Left panel — entity list
        if mx < PANEL_W:
            entity_section_h = min(len(self.entity_names) * ITEM_H + ITEM_H, WINDOW_H // 2)

            if ITEM_H <= my < entity_section_h:
                idx = (my - ITEM_H + self.entity_scroll) // ITEM_H
                if 0 <= idx < len(self.entity_names):
                    self.selected_entity = idx
                    self.selected_anim = 0
                    self._rebuild_anim_list()
                    self._load_selected_animation()
                    self.playing = False
                return

            anim_y_start = entity_section_h + ITEM_H
            if my >= anim_y_start:
                idx = (my - anim_y_start + self.anim_scroll) // ITEM_H
                if 0 <= idx < len(self.anim_names):
                    self.selected_anim = idx
                    self._load_selected_animation()
                    self.playing = False
            return

        # Buttons
        btn_y = WINDOW_H - BTN_H - 6
        btn_play = pygame.Rect(PREVIEW_X + 20, btn_y, 100, BTN_H)
        btn_stop = pygame.Rect(PREVIEW_X + 140, btn_y, 100, BTN_H)
        btn_prev = pygame.Rect(PREVIEW_X + 260, btn_y, 50, BTN_H)
        btn_next = pygame.Rect(PREVIEW_X + 320, btn_y, 50, BTN_H)
        btn_slower = pygame.Rect(PREVIEW_X + 390, btn_y, 36, BTN_H)
        btn_faster = pygame.Rect(PREVIEW_X + 520, btn_y, 36, BTN_H)

        if btn_play.collidepoint(mx, my):
            if self.frames:
                self.playing = True
                if self.current_frame >= len(self.frames) - 1:
                    self.current_frame = 0
                    self.elapsed = 0.0
        elif btn_stop.collidepoint(mx, my):
            self.playing = False
        elif btn_prev.collidepoint(mx, my):
            self.playing = False
            if self.frames:
                self.current_frame = (self.current_frame - 1) % len(self.frames)
        elif btn_next.collidepoint(mx, my):
            self.playing = False
            if self.frames:
                self.current_frame = (self.current_frame + 1) % len(self.frames)
        elif btn_slower.collidepoint(mx, my):
            self.frame_duration = round(min(1.0, self.frame_duration + 0.01), 3)
            self._save_frame_duration()
        elif btn_faster.collidepoint(mx, my):
            self.frame_duration = round(max(0.01, self.frame_duration - 0.01), 3)
            self._save_frame_duration()

        # Scale buttons
        btn_scale_down = pygame.Rect(PREVIEW_X + 580, btn_y, 36, BTN_H)
        btn_scale_up = pygame.Rect(PREVIEW_X + 700, btn_y, 36, BTN_H)
        if btn_scale_down.collidepoint(mx, my):
            self.cur_scale = round(max(0.5, self.cur_scale - 0.5), 1)
            self._save_scale()
        elif btn_scale_up.collidepoint(mx, my):
            self.cur_scale = round(self.cur_scale + 0.1, 1)
            self._save_scale()


if __name__ == "__main__":
    tester = AnimationTester()
    tester.run()
