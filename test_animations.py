#!/usr/bin/env python
"""Quick test of animation loading"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PYGAME_DIR = PROJECT_ROOT / "pygame"
SCRIPTS_DIR = PYGAME_DIR / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))

from resource_manager import AnimationCache

# Test animation loading
cache = AnimationCache()
animations_json = PYGAME_DIR / "data" / "animations_config.json"

print(f"Testing animation loading from: {animations_json}")
if cache.load_animations_from_json(str(animations_json)):
    print("\n=== ANIMATION LOAD SUCCESSFUL ===")
    for entity in cache.list_entities():
        print(f"\nEntity: {entity}")
        for anim in cache.list_animations(entity):
            frame_count = cache.get_frame_count(entity, anim)
            print(f"  - {anim}: {frame_count} frames")
else:
    print("\n=== ANIMATION LOAD FAILED ===")
