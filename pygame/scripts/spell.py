"""
Spell System Module - Active spell effects and spell management.

Classes:
    SpellEffect: Individual active spell instance with animation, hitbox, and effects
    SpellManager: Manages spell casting, active effects, updates, and rendering
"""

import pygame
import math
import json
from pathlib import Path
from typing import List, Optional

_STAT_CONFIG_PATH = Path(__file__).parent.parent / "data" / "stat_config.json"
with open(_STAT_CONFIG_PATH, "r") as _f:
    STAT_CONFIG = json.load(_f)

SPELL_NAMES = sorted(
    STAT_CONFIG["spells"].keys(),
    key=lambda s: STAT_CONFIG["spells"][s]["index"]
)


class SpellEffect:
    """A single active spell instance in the world."""

    def __init__(self, spell_name: str, config: dict, x: float, y: float,
                 frames: list, frame_duration: float, target_monster=None):
        self.spell_name = spell_name
        self.config = config
        self.x = x
        self.y = y
        self.frames = frames
        self.frame_duration = frame_duration
        self.current_frame_index = 0
        self.elapsed_time = 0.0
        self.finished = False
        self.has_applied_damage = False
        self.target_monster = target_monster
        self.hit_monsters: list = []

        # For special effects
        self.special = config.get("special")
        self.second_hit_timer = -1  # double_hit
        self.explosion_timer = -1   # delayed_explosion
        self.marked_x = 0.0
        self.marked_y = 0.0

        # delayed_explosion: mark position, no immediate damage
        if self.special == "delayed_explosion":
            self.explosion_timer = 3.0
            self.has_applied_damage = True  # skip immediate damage

    def get_hitbox(self) -> pygame.Rect:
        hb = self.config["hitbox"]
        return pygame.Rect(
            self.x + hb["offset_x"], self.y + hb["offset_y"],
            hb["width"], hb["height"]
        )

    def update(self, dt: float):
        if self.finished:
            return
        self.elapsed_time += dt
        if self.elapsed_time >= self.frame_duration:
            self.elapsed_time -= self.frame_duration
            self.current_frame_index += 1
            if self.current_frame_index >= len(self.frames):
                self.finished = True

    def draw(self, surface: pygame.Surface, debug: bool = False):
        if self.finished or not self.frames:
            return
        frame = self.frames[min(self.current_frame_index, len(self.frames) - 1)]
        anim_ox = self.config.get("anim_offset_x", 0)
        anim_oy = self.config.get("anim_offset_y", 0)
        # AOE: bottom-center of animation at (x, y); ST: center at (x, y)
        fx = int(self.x - frame.get_width() / 2 + anim_ox)
        if self.config["type"] == "AOE":
            fy = int(self.y - frame.get_height() + anim_oy)
        else:
            fy = int(self.y - frame.get_height() / 2 + anim_oy)
        surface.blit(frame, (fx, fy))

        if debug:
            hb = self.get_hitbox()
            pygame.draw.rect(surface, (0, 255, 0), hb, 2)

    def apply_effects(self, all_monsters: list) -> list:
        """Apply damage and status effects. Returns list of new SpellEffects to spawn."""
        if self.has_applied_damage:
            return []
        self.has_applied_damage = True

        hitbox = self.get_hitbox()
        cfg = self.config
        new_spells = []

        # Find targets
        targets = []
        if cfg["type"] == "ST":
            if self.target_monster and self.target_monster.is_alive():
                targets = [self.target_monster]
        else:  # AOE
            for m in all_monsters:
                if not m.is_alive() or getattr(m, '_dying', False):
                    continue
                m_rect = pygame.Rect(
                    getattr(m, 'col_x', m.x),
                    getattr(m, 'col_y', m.y),
                    getattr(m, 'collision_width', 40),
                    getattr(m, 'collision_height', 40)
                )
                if hitbox.colliderect(m_rect):
                    targets.append(m)

        # Apply damage and effects to each target
        for m in targets:
            m.take_spell_damage(cfg["damage"])
            self.hit_monsters.append(m)

            if cfg.get("burn_duration", 0) > 0 and cfg.get("burn_damage", 0) > 0:
                m.apply_burn(cfg["burn_damage"], cfg["burn_duration"])

            if cfg.get("stun_duration", 0) > 0:
                m.apply_stun(cfg["stun_duration"])

            if cfg.get("freeze_duration", 0) > 0:
                m.apply_freeze(
                    cfg["freeze_duration"],
                    cfg.get("slow_value", 0),
                    cfg.get("slow_duration", 0)
                )
            elif cfg.get("slow_duration", 0) > 0 and cfg.get("slow_value", 0) > 0:
                m.apply_slow(cfg["slow_value"], cfg["slow_duration"])

            if cfg.get("knockback_force", 0) > 0:
                dx = (getattr(m, 'col_x', m.x) + getattr(m, 'collision_width', 0) / 2) - self.x
                dy = (getattr(m, 'col_y', m.y) + getattr(m, 'collision_height', 0) / 2) - self.y
                dist = max((dx**2 + dy**2) ** 0.5, 1)
                m.apply_knockback(
                    cfg["knockback_force"],
                    dx / dist, dy / dist
                )

            if cfg.get("knockup_duration", 0) > 0:
                m.apply_knockup(cfg["knockup_duration"])

        # Handle special effects
        if self.special == "chain":
            new_spells.extend(self._handle_chain(all_monsters))
        elif self.special == "curse_spread":
            for m in targets:
                m.cursed = True
        elif self.special == "double_hit":
            self.marked_x = self.x
            self.marked_y = self.y
            self.second_hit_timer = 0.5
        elif self.special == "kill_bonus":
            self._handle_kill_bonus(all_monsters)

        return new_spells

    def _handle_chain(self, all_monsters: list) -> list:
        """Lightning chain: if target killed, chain to nearest alive monster."""
        new_spells = []
        for m in self.hit_monsters:
            if not m.is_alive():
                nearest = None
                best_dist = float('inf')
                mx = getattr(m, 'col_x', m.x) + getattr(m, 'collision_width', 0) / 2
                my = getattr(m, 'col_y', m.y) + getattr(m, 'collision_height', 0) / 2
                for other in all_monsters:
                    if other in self.hit_monsters or not other.is_alive() or getattr(other, '_dying', False):
                        continue
                    ox = getattr(other, 'col_x', other.x) + getattr(other, 'collision_width', 0) / 2
                    oy = getattr(other, 'col_y', other.y) + getattr(other, 'collision_height', 0) / 2
                    d = ((mx - ox)**2 + (my - oy)**2) ** 0.5
                    if d < best_dist:
                        best_dist = d
                        nearest = other
                if nearest:
                    ox = getattr(nearest, 'col_x', nearest.x) + getattr(nearest, 'collision_width', 0) / 2
                    oy = getattr(nearest, 'col_y', nearest.y) + getattr(nearest, 'collision_height', 0) / 2
                    new_spells.append({
                        "spell_name": self.spell_name,
                        "x": ox, "y": oy,
                        "target": nearest
                    })
        return new_spells

    def _handle_kill_bonus(self, all_monsters: list):
        """Crystal: killed targets deal bonus damage to nearby monsters."""
        hb = self.config["hitbox"]
        bonus_radius = max(hb["width"], hb["height"])
        bonus_damage = int(self.config["damage"] * 0.5)
        for m in self.hit_monsters:
            if not m.is_alive():
                mx = getattr(m, 'col_x', m.x) + getattr(m, 'collision_width', 0) / 2
                my = getattr(m, 'col_y', m.y) + getattr(m, 'collision_height', 0) / 2
                for other in all_monsters:
                    if other is m or not other.is_alive() or getattr(other, '_dying', False):
                        continue
                    ox = getattr(other, 'col_x', other.x) + getattr(other, 'collision_width', 0) / 2
                    oy = getattr(other, 'col_y', other.y) + getattr(other, 'collision_height', 0) / 2
                    if ((mx - ox)**2 + (my - oy)**2) ** 0.5 <= bonus_radius:
                        other.take_spell_damage(bonus_damage)


class SpellManager:
    """Manages spell casting, active spell effects, and rendering."""

    def __init__(self, animation_cache):
        self.animation_cache = animation_cache
        self.spell_configs = STAT_CONFIG["spells"]
        self.active_spells: List[SpellEffect] = []
        self.selected_spell_index: int = 0

    def get_selected_spell_name(self) -> str:
        if 0 <= self.selected_spell_index < len(SPELL_NAMES):
            return SPELL_NAMES[self.selected_spell_index]
        return SPELL_NAMES[0]

    def cast(self, player, monsters: list) -> bool:
        """Cast the selected spell at the nearest monster. Returns True on success."""
        spell_name = self.get_selected_spell_name()
        cfg = self.spell_configs[spell_name]

        if player.mana < cfg["mana_cost"]:
            print(f"[SPELL] Not enough mana for {spell_name} (need {cfg['mana_cost']}, have {player.mana})")
            return False

        # Find nearest alive monster
        target = self._find_nearest_monster(player, monsters)
        if target is None:
            print(f"[SPELL] No target for {spell_name}")
            return False

        player.mana -= cfg["mana_cost"]

        # Spawn position: target collision center
        tx = getattr(target, 'col_x', target.x) + getattr(target, 'collision_width', 0) / 2
        ty = getattr(target, 'col_y', target.y) + getattr(target, 'collision_height', 0) / 2

        spell_effect = self._create_spell_effect(spell_name, cfg, tx, ty, target)
        if spell_effect:
            self.active_spells.append(spell_effect)
            print(f"[SPELL] Cast {spell_name} at ({tx:.0f}, {ty:.0f})")
            return True
        return False

    def _find_nearest_monster(self, player, monsters: list):
        px = player.col_x + player.collision_width / 2
        py = player.col_y + player.collision_height / 2
        best = None
        best_dist = float('inf')
        for m in monsters:
            if not m.is_alive() or getattr(m, '_dying', False):
                continue
            mx = getattr(m, 'col_x', m.x) + getattr(m, 'collision_width', 0) / 2
            my = getattr(m, 'col_y', m.y) + getattr(m, 'collision_height', 0) / 2
            d = ((px - mx)**2 + (py - my)**2) ** 0.5
            if d < best_dist:
                best_dist = d
                best = m
        return best

    def _create_spell_effect(self, spell_name: str, cfg: dict,
                             x: float, y: float, target=None) -> Optional[SpellEffect]:
        spell_anims = self.animation_cache.animations.get("spell", {})
        frames = spell_anims.get(spell_name, [])
        if not frames:
            print(f"[SPELL] No animation frames for {spell_name}")
            return None
        frame_duration = 0.08
        return SpellEffect(spell_name, cfg, x, y, frames, frame_duration, target_monster=target)

    def update(self, dt: float, all_monsters: list):
        pending = []
        for spell in self.active_spells:
            spell.update(dt)

            # Apply damage on first frame
            if not spell.has_applied_damage:
                new_spells = spell.apply_effects(all_monsters)
                for ns in new_spells:
                    effect = self._create_spell_effect(
                        ns["spell_name"],
                        self.spell_configs[ns["spell_name"]],
                        ns["x"], ns["y"], ns.get("target")
                    )
                    if effect:
                        pending.append(effect)

            # Double hit timer
            if spell.second_hit_timer > 0:
                spell.second_hit_timer -= dt
                if spell.second_hit_timer <= 0:
                    effect = self._create_spell_effect(
                        spell.spell_name, spell.config,
                        spell.marked_x, spell.marked_y, None
                    )
                    if effect:
                        # Double hit is AOE at marked position
                        pending.append(effect)

            # Delayed explosion timer
            if spell.explosion_timer > 0:
                spell.explosion_timer -= dt
                if spell.explosion_timer <= 0:
                    # Spawn actual damage effect
                    cfg_copy = dict(spell.config)
                    cfg_copy["special"] = None  # don't recurse
                    effect = SpellEffect(
                        spell.spell_name, cfg_copy,
                        spell.x, spell.y,
                        spell.frames[:], spell.frame_duration, None
                    )
                    pending.append(effect)

        self.active_spells.extend(pending)

        # Remove finished spells (no pending timers)
        self.active_spells = [
            s for s in self.active_spells
            if not s.finished or s.second_hit_timer > 0 or s.explosion_timer > 0
        ]

    def update_curse_spread(self, all_monsters: list):
        """Dark curse: cursed monsters spread curse on collision with non-cursed."""
        cursed = [m for m in all_monsters if getattr(m, 'cursed', False) and m.is_alive()]
        for cm in cursed:
            c_rect = pygame.Rect(
                getattr(cm, 'col_x', cm.x), getattr(cm, 'col_y', cm.y),
                getattr(cm, 'collision_width', 40), getattr(cm, 'collision_height', 40)
            )
            for other in all_monsters:
                if other is cm or getattr(other, 'cursed', False) or not other.is_alive():
                    continue
                o_rect = pygame.Rect(
                    getattr(other, 'col_x', other.x), getattr(other, 'col_y', other.y),
                    getattr(other, 'collision_width', 40), getattr(other, 'collision_height', 40)
                )
                if c_rect.colliderect(o_rect):
                    other.cursed = True
                    dark_cfg = self.spell_configs.get("dark", {})
                    if dark_cfg.get("burn_duration", 0) > 0:
                        other.apply_burn(dark_cfg["burn_damage"], dark_cfg["burn_duration"])

    def draw(self, surface: pygame.Surface, debug: bool = False):
        for spell in self.active_spells:
            spell.draw(surface, debug)
