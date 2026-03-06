"""
Sprite Sheet Example - Demonstrates how to use sprite animations with VFX library
This shows the pattern for integrating sprite sheets into the spell recognizer.
"""

import cv2
import numpy as np
from pathlib import Path
from vfx_library import extract_sprites, SpriteEffect, VFXManager


def setup_sprite_effects():
    """
    Setup sprite-based effects by loading sprite sheets.
    
    Returns:
        VFXManager with sprite effects, or None if sprites not found
    """
    sprites_dir = Path(__file__).parent / "assets" / "sprites"
    
    # Create VFX manager
    vfx_manager = VFXManager()
    
    # List of sprite sheets to load
    sprite_configs = [
        {
            'name': 'Tiger',
            'file': 'fireball.png',
            'rows': 4,
            'cols': 4,
            'duration': 60,
            'frame_skip': 2,
            'scale': 1.5
        },
        {
            'name': 'Dragon',
            'file': 'ice.png',
            'rows': 4,
            'cols': 4,
            'duration': 60,
            'frame_skip': 2,
            'scale': 1.5
        },
        {
            'name': 'Ox',
            'file': 'lightning.png',
            'rows': 4,
            'cols': 4,
            'duration': 60,
            'frame_skip': 2,
            'scale': 1.5
        },
    ]
    
    print("\n" + "="*60)
    print("Loading Sprite Sheets")
    print("="*60)
    
    sprites_loaded = 0
    
    for config in sprite_configs:
        sprite_path = sprites_dir / config['file']
        
        if sprite_path.exists():
            # Extract sprites from sheet
            sprites = extract_sprites(
                str(sprite_path),
                config['rows'],
                config['cols']
            )
            
            if sprites:
                # Create sprite effect
                effect = SpriteEffect(
                    sprite_frames=sprites,
                    duration=config['duration'],
                    frame_skip=config['frame_skip'],
                    scale=config['scale']
                )
                
                # Replace effect in manager
                vfx_manager.effects[config['name']] = effect
                vfx_manager.effects[config['file'].split('.')[0]] = effect
                
                sprites_loaded += 1
                print(f"✓ {config['name']}: {len(sprites)} frames loaded")
        else:
            print(f"⚠ {config['name']}: Sprite file not found at {sprite_path}")
    
    print("="*60)
    
    if sprites_loaded > 0:
        print(f"✓ Successfully loaded {sprites_loaded} sprite effects")
        return vfx_manager
    else:
        print("✗ No sprite sheets found, using procedural effects")
        return vfx_manager  # Return default effects


def test_sprite_rendering():
    """
    Test sprite rendering with keyboard controls.
    Press:
      1: Trigger Tiger (Fireball)
      2: Trigger Dragon (Ice)
      3: Trigger Ox (Lightning)
      S: Save frame
      Q: Quit
    """
    
    # Setup VFX manager with sprites
    vfx_manager = setup_sprite_effects()
    
    print("\n" + "="*60)
    print("Sprite Animation Test")
    print("="*60)
    print("\nControls:")
    print("  1: Cast Fireball (Tiger)")
    print("  2: Cast Ice (Dragon)")
    print("  3: Cast Lightning (Ox)")
    print("  S: Save frame to output/")
    print("  Q: Quit")
    print("="*60 + "\n")
    
    # Create blank canvas
    width, height = 1280, 720
    center = (width // 2, height // 2)
    
    frame_counter = 0
    saved_frames = 0
    
    while True:
        # Create blank frame
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add background gradient
        for y in range(height):
            intensity = int(30 + (y / height) * 50)
            frame[y, :] = [intensity, intensity, intensity]
        
        # Add center marker
        cv2.circle(frame, center, 10, (100, 200, 255), 1)
        cv2.circle(frame, center, 3, (100, 200, 255), -1)
        
        # Update and render all active effects
        vfx_manager.update_and_draw(frame, center)
        
        # Add info text
        info_lines = [
            f"Frame: {frame_counter}",
            f"Active spells: {len(vfx_manager.get_active_spells())}",
            f"Saved frames: {saved_frames}"
        ]
        
        for i, text in enumerate(info_lines):
            cv2.putText(
                frame,
                text,
                (10, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
        
        # Show help
        help_lines = [
            "1: Fireball    2: Ice    3: Lightning",
            "S: Save        Q: Quit"
        ]
        
        for i, text in enumerate(help_lines):
            cv2.putText(
                frame,
                text,
                (width - 400, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1
            )
        
        # Display frame
        cv2.imshow("Sprite Animation Test", frame)
        
        # Handle keyboard input
        key = cv2.waitKey(33) & 0xFF  # ~30 FPS
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key == ord('1'):
            vfx_manager.trigger_spell('Tiger')
            print("✨ Triggered Fireball (Tiger)")
        elif key == ord('2'):
            vfx_manager.trigger_spell('Dragon')
            print("❄️  Triggered Ice (Dragon)")
        elif key == ord('3'):
            vfx_manager.trigger_spell('Ox')
            print("⚡ Triggered Lightning (Ox)")
        elif key == ord('s') or key == ord('S'):
            # Save frame
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            
            filename = f"sprite_frame_{frame_counter:04d}.jpg"
            filepath = output_dir / filename
            
            cv2.imwrite(str(filepath), frame)
            print(f"💾 Saved: {filename}")
            saved_frames += 1
        
        frame_counter += 1
    
    cv2.destroyAllWindows()
    print("\n✓ Test completed")


if __name__ == "__main__":
    try:
        test_sprite_rendering()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
