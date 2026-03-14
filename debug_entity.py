#!/usr/bin/env python
"""Debug script to check entity rendering and animation frames"""
import sys
import pygame
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PYGAME_DIR = PROJECT_ROOT / "pygame"
SCRIPTS_DIR = PYGAME_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from resource_manager import AnimationCache
from entity import Player, Monster

# Initialize pygame
pygame.init()

# Load animations
cache = AnimationCache()
animations_json = PYGAME_DIR / "data" / "animations_config.json"
cache.load_animations_from_json(str(animations_json))

print("\n=== WIZARD ANIMATION DEBUG ===")
wizard = Player(x=320, y=240, animation_cache=cache, name="Wizard")

print(f"Wizard position: ({wizard.x}, {wizard.y})")
print(f"Wizard animations available: {list(wizard.animations.keys())}")

# Check idle animation
idle_frames = wizard.animations.get("idle")
if idle_frames:
    print(f"\nIdle animation: {len(idle_frames)} frames")
    for i, frame in enumerate(idle_frames[:3]):  # Show first 3 frames
        print(f"  Frame {i}: {frame.get_width()}x{frame.get_height()} pixels")
else:
    print("ERROR: No idle animation found!")

# Simulate animation updates
print("\n=== ANIMATION PLAYBACK TEST ===")
print(f"Initial frame index: {wizard.current_frame_index}")
print(f"Initial elapsed time: {wizard.elapsed_time}")

for step in range(10):
    wizard.update(0.05)  # 50ms per frame
    idle_set = wizard.animations.get(wizard.state.value)
    if idle_set:
        current_frame = idle_set[wizard.current_frame_index % len(idle_set)]
        print(f"Step {step}: frame_idx={wizard.current_frame_index}, {current_frame.get_width()}x{current_frame.get_height()}")
