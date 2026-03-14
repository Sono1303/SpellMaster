#!/usr/bin/env python
"""Inspect sprite sheet and frame extraction"""
import sys
import pygame
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
PYGAME_DIR = PROJECT_ROOT / "pygame"

pygame.init()

# Load wizard idle sprite sheet
wizard_idle_path = PYGAME_DIR / "ingame_assets" / "character" / "wizard" / "Wizard_Idle.png"
print(f"Loading sprite sheet: {wizard_idle_path}")
print(f"File exists: {wizard_idle_path.exists()}\n")

if wizard_idle_path.exists():
    sheet = pygame.image.load(str(wizard_idle_path))
    print(f"Sprite sheet dimensions: {sheet.get_width()}x{sheet.get_height()} pixels")
    
    # Calculate frames per row with 64x64 frame size
    frame_width, frame_height = 64, 64
    frames_per_row = sheet.get_width() // frame_width
    rows_total = sheet.get_height() // frame_height
    
    print(f"Frame size: {frame_width}x{frame_height}")
    print(f"Frames per row: {frames_per_row}")
    print(f"Total rows: {rows_total}")
    print(f"Total possible frames: {frames_per_row * rows_total}")
    
    print("\n=== FRAME EXTRACTION TEST ===")
    print("Extracting 7 frames starting at [0, 0]:\n")
    
    # Simulate frame extraction with wrapping
    start_row, start_col = 0, 0
    frame_count = 7
    
    for i in range(frame_count):
        linear_pos = start_col + i
        grid_col = linear_pos % frames_per_row
        grid_row = start_row + linear_pos // frames_per_row
        
        pixel_x = grid_col * frame_width
        pixel_y = grid_row * frame_height
        
        print(f"Frame {i}:")
        print(f"  Linear pos: {linear_pos}")
        print(f"  Grid pos: [{grid_row}, {grid_col}]")
        print(f"  Pixel pos: ({pixel_x}, {pixel_y})")
        print(f"  Bounds check: ({pixel_x}+{frame_width}, {pixel_y}+{frame_height}) vs ({sheet.get_width()}, {sheet.get_height()})")
        
        if pixel_x + frame_width > sheet.get_width() or pixel_y + frame_height > sheet.get_height():
            print(f"  STATUS: OUT OF BOUNDS")
        else:
            print(f"  STATUS: OK")
        print()
