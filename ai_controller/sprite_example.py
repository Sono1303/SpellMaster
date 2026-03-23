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
        tuple: (VFXManager with sprite effects, sprite_configs with metadata)
    """
    sprites_dir = Path(__file__).parent / "assets" / "sprites"
    
    # Create VFX manager
    vfx_manager = VFXManager()
    
    # List of sprite sheets to load - now with custom key bindings
    sprite_configs = [
        {
            'name': 'Tiger',
            'display_name': 'Fireball (Tiger)',
            'file': 'fireball.png',
            'rows': 4,
            'cols': 4,
            'duration': 60,
            'frame_skip': 2,
            'scale': 10,
            'key': '1'
        },
        {
            'name': 'phoenix',
            'display_name': 'phoenix (Phoenix)',
            'file': 'phoenix.png',
            'rows': 1,
            'cols': 18,
            'duration': 60,
            'frame_skip': 2,
            'scale': 10,
            'key': '2'
        },
        {
            'name': 'Ox',
            'display_name': 'crystal (Ox)',
            'file': 'crystal.png',
            'rows': 1,
            'cols': 13,
            'duration': 60,
            'frame_skip': 2,
            'scale': 5,
            'key': '3'
        },
                {
            'name': 'Water Spike',
            'display_name': 'Water Spike (Water)',
            'file': 'water_spike.png',
            'rows': 4,
            'cols': 5,
            'duration': 60,
            'frame_skip': 2,
            'scale': 5,
            'key': '4'
        },
        {
            'name': 'Thunder',
            'display_name': 'Thunder (Thunder)',
            'file': 'thunder.png',
            'rows': 1,
            'cols': 13,
            'duration': 60,
            'frame_skip': 2,
            'scale': 5,
            'key': '5'
        },
        {
            'name': 'air',
            'display_name': 'Air (Air)',
            'file': 'air.png',
            'rows': 3,
            'cols': 4,
            'duration': 60,
            'frame_skip': 2,
            'scale': 10,
            'key': '6'
        },
            {
                'name': 'earth',
                'display_name': 'Earth (Earth)',
                'file': 'earth.png',
                'rows': 2,
                'cols': 6,
                'duration': 60,
                'frame_skip': 2,
                'scale': 10,
                'key': '7'
            },
            {
                'name': 'ice',
                'display_name': 'Ice (Ice)',
                'file': 'ice3.png',
                'rows': 1,
                'cols': 8,
                'duration': 60,
                'frame_skip': 2,
                'scale': 10,
                'key': '8'
            },
            {
                'name': 'dark',
                'display_name': 'Dark',
                'file': 'dark.png',
                'rows': 1,
                'cols': 16,
                'duration': 60,
                'frame_skip': 2,
                'scale': 10,
                'key': '9'
            },
            {
                'name': 'light',
                'display_name': 'Light',
                'file': 'light.png',
                'rows': 1,
                'cols': 7,
                'duration': 60,
                'frame_skip': 2,
                'scale': 10,
                'key': '0'
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
    else:
        print("✗ No sprite sheets found, using procedural effects")
    
    return vfx_manager, sprite_configs  # Return both manager and configs


def test_sprite_rendering():
    """
    Test sprite rendering with keyboard controls (dynamically generated from sprite_configs).
    Controls are automatically generated based on the 'key' field in each sprite config.
    """
    
    # Setup VFX manager with sprites and get configs
    vfx_manager, sprite_configs = setup_sprite_effects()
    
    print("\n" + "="*60)
    print("Sprite Animation Test")
    print("="*60)
    print("\nControls:")
    
    # Build key mapping from configs
    key_mapping = {}
    for config in sprite_configs:
        key = config['key']
        name = config['display_name']
        spell_name = config['name']
        
        # Handle multi-character keys (e.g., '10') - use first character only
        if len(key) == 1:
            key_code = ord(key)
        else:
            # For multi-character keys like '10', just use the first character
            key_code = ord(key[0])
        
        key_mapping[key_code] = {
            'spell_name': spell_name,
            'display_name': name
        }
        print(f"  {key}: {name}")
    
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
            " | ".join([f"{cfg['key']}: {cfg['display_name']}" for cfg in sprite_configs]),
            "S: Save        Q: Quit"
        ]
        
        for i, text in enumerate(help_lines):
            cv2.putText(
                frame,
                text,
                (width - 700, 30 + i * 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1
            )
        
        # Display frame
        cv2.imshow("Sprite Animation Test", frame)
        
        # Handle keyboard input
        key = cv2.waitKey(33) & 0xFF  # ~30 FPS
        
        if key == ord('q') or key == ord('Q'):
            break
        elif key in key_mapping:
            # Dynamically handle spells from key_mapping
            spell_info = key_mapping[key]
            vfx_manager.trigger_spell(spell_info['spell_name'])
            print(f"✨ Triggered {spell_info['display_name']}")
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
