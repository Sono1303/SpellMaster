#!/usr/bin/env python
"""Test updated frame extraction"""
import sys
import pygame
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PYGAME_DIR = PROJECT_ROOT / "pygame"

pygame.init()

# Load wizard idle sprite sheet
wizard_idle_path = PYGAME_DIR / "ingame_assets" / "character" / "wizard" / "Wizard_Idle.png"
sheet = pygame.image.load(str(wizard_idle_path))

print(f"Sprite sheet: {sheet.get_width()}x{sheet.get_height()} pixels")
print(f"NEW frame size: 65x77")

frame_width, frame_height = 65, 77
frames_per_row = sheet.get_width() // frame_width

print(f"Frames per row: {frames_per_row}")

print("\n=== EXTRACTING 7 FRAMES ===")
for i in range(7):
    linear_pos = i
    grid_col = linear_pos % frames_per_row
    grid_row = 0
    
    pixel_x = grid_col * frame_width
    pixel_y = grid_row * frame_height
    
    bounds_ok = (pixel_x + frame_width <= sheet.get_width() and 
                 pixel_y + frame_height <= sheet.get_height())
    
    print(f"Frame {i}: pos=({pixel_x:3d}, {pixel_y:3d}) size=65x77 → {bounds_ok and 'OK' or 'OUT OF BOUNDS'}")
