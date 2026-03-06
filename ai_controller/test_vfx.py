"""
VFX Library Test Script
Tests VFX effects rendering without requiring webcam or model
"""

import cv2
import numpy as np
from vfx_library import VFXManager, FireballEffect, IceEffect, LightningEffect

def test_vfx_effects():
    """Test all VFX effects on a blank canvas."""
    
    print("Testing VFX Library...")
    
    # Create VFX manager
    vfx_manager = VFXManager()
    print(f"✓ VFXManager initialized")
    print(f"  Available effects: {list(vfx_manager.effects.keys())}")
    
    # Create blank canvas
    width, height = 1280, 720
    
    # Test each effect
    effects_to_test = ['Tiger', 'Dragon', 'Ox']
    center = (width // 2, height // 2)
    
    print(f"\nTesting effects at center: {center}")
    print("=" * 50)
    
    for effect_name in effects_to_test:
        print(f"\nTesting {effect_name} effect...")
        
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Trigger spell
        vfx_manager.trigger_spell(effect_name)
        print(f"✓ {effect_name} triggered")
        
        # Simulate 30 frames of rendering
        for frame_idx in range(30):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            
            # Update and draw
            vfx_manager.update_and_draw(frame, center)
            
            # Add frame counter text
            cv2.putText(frame, f"Frame: {frame_idx}/30 - {effect_name}", 
                       (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            # Show live
            cv2.imshow("VFX Test", frame)
            
            if cv2.waitKey(33) & 0xFF == ord('q'):
                break
        
        print(f"✓ {effect_name} rendered successfully")
    
    cv2.destroyAllWindows()
    print("\n" + "=" * 50)
    print("✓ All VFX tests completed successfully!")
    print("\nNext steps:")
    print("1. Run: python spell_recognizer.py")
    print("2. Perform hand gestures with both hands on camera")
    print("3. Watch VFX effects trigger when confidence > 80%")

if __name__ == "__main__":
    try:
        test_vfx_effects()
    except Exception as e:
        print(f"✗ Error during VFX test: {e}")
        import traceback
        traceback.print_exc()
