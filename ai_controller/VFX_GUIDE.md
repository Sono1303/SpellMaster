# Spell Recognition System with VFX Effects

A real-time gesture recognition system that detects spell hand gestures and renders dynamic visual effects using OpenCV and MediaPipe.

## System Architecture

### File Structure

```
SpellMaster/
├── ai_controller/
│   ├── spell_recognizer.py      # Main recognizer with VFX integration
│   ├── vfx_library.py           # VFX effects library
│   ├── data/
│   │   ├── best_spell_model.pkl # Trained ML model
│   │   └── data_collector.py    # Data collection script
│   └── gesture_model_battle.py  # Model training
└── requirements.txt
```

## Features

### 1. **Real-time Spell Recognition**

- Detects dual-hand gestures using MediaPipe (21 landmarks per hand)
- Uses trained ML model (Random Forest/SVM) for classification
- Requires **exactly 2 hands** for spell detection
- Confidence threshold: 75% (adjustable)
- VFX trigger threshold: 80%

### 2. **Visual Effects (VFX)**

#### **Fireball (Tiger Spell) 🔥**

- Concentric circles: Red → Orange → Yellow
- Gaussian blur glow effect for realism
- 30-frame duration with automatic fade-out
- Alpha blending for smooth transparency

#### **Ice Shards (Dragon Spell) ❄️**

- Cyan overlay with transparency
- 12 randomly positioned diamond/rhombus shapes
- Animated ice fragments radiating from center
- Smooth fade animation

#### **Lightning/Chidori (Ox Spell) ⚡**

- 8 zigzag lightning bolts radiating from center
- White core with cyan outer glow
- Gaussian blur bloom effect
- Dynamic path with random zigzag pattern

### 3. **Effect Management System**

Each effect has:

- **Timer System**: `duration` frames countdown to fade-out
- **Alpha Blending**: Smooth fade based on remaining duration
- **Dynamic Positioning**: Follows bounding box center in real-time
- **Non-blocking**: Effects don't interrupt recognition

## Usage

### Basic Execution

```powershell
cd D:\AI-2026
python SpellMaster\ai_controller\spell_recognizer.py
```

### Keyboard Controls

- **Q/Esc**: Exit application
- **S**: Manual start recording (if mode changed)
- **N**: Set new label
- **+/-**: Adjust smoothing factor

### VFX Triggering

Gestures trigger VFX when:

1. **Exactly 2 hands** are detected
2. Confidence score **> 80%**
3. Different spell from last trigger (prevents re-triggering)

## Recognized Spells

| Spell Name | Gesture                 | VFX Effect    | Confidence |
| ---------- | ----------------------- | ------------- | ---------- |
| Tiger      | Interlocked fingers     | Fireball 🔥   | > 75%      |
| Dragon     | Palms facing each other | Ice Shards ❄️ | > 75%      |
| Ox         | Hands crossed           | Lightning ⚡  | > 75%      |

## Code Integration

### VFX Library (`vfx_library.py`)

**Main Classes:**

```python
class VFXManager:
    """Manages all VFX effects"""
    - trigger_spell(spell_label)      # Activate effect
    - update_and_draw(frame, center)  # Render effects
    - is_any_active()                 # Check active effects
    - get_active_spells()             # List active effects

class FireballEffect(VFXEffect):
    """Fireball VFX"""

class IceEffect(VFXEffect):
    """Ice Shards VFX"""

class LightningEffect(VFXEffect):
    """Lightning VFX"""
```

**Key Functions:**

```python
def overlay_png(frame, png_image, position, alpha=0.7)
    # Overlay PNG with alpha transparency

def draw_vfx(frame, effect_type, center_coord, vfx_manager)
    # Main VFX rendering function
```

### Spell Recognizer Integration (`spell_recognizer.py`)

```python
class SpellRecognizer:
    def __init__(self):
        self.vfx_manager = VFXManager()  # Initialize VFX

    def trigger_vfx_for_spell(self, spell_name, center_coord)
        # Map spell name to VFX and trigger

    def run(self):
        # Main loop:
        # 1. Detect hands
        # 2. Recognize spell
        # 3. Trigger VFX if confidence > 80%
        # 4. Render effects and bounding box
```

## Performance Considerations

- **FPS**: Optimized for 30+ FPS on modern hardware
- **Memory**: VFX uses in-place frame operations (minimal overhead)
- **CPU**: MediaPipe Complex 1 + OpenCV ops ~100-150ms per frame
- **Optimization**: Gaussian blur kernel size scaled by effect alpha

## Customization

### Adjust Effect Duration

```python
# In vfx_library.py, VFXManager.__init__:
self.effects = {
    'Tiger': FireballEffect(duration=45),  # Longer fireball
    'Dragon': IceEffect(duration=35),
    'Ox': LightningEffect(duration=40),
}
```

### Change VFX Colors

```python
# In FireballEffect.draw():
colors = [
    (0, 0, 255),      # Red
    (0, 165, 255),    # Orange
    (0, 255, 255)     # Yellow
]
```

### Modify Effect Threshold

```python
# In spell_recognizer.py, run():
if confidence > 85:  # Change from 80 to 85
    self.trigger_vfx_for_spell(...)
```

## Troubleshooting

### Issue: VFX not appearing

1. Check confidence > 80% (console output shows percentage)
2. Ensure exactly 2 hands are detected (UI shows count)
3. Verify spell name matches mapping in `trigger_vfx_for_spell()`

### Issue: Low FPS

1. Reduce effect complexity (smaller blur kernels)
2. Decrease max_radius in effect classes
3. Lower detection confidence threshold (may reduce accuracy)

### Issue: Effects appearing in wrong location

1. Ensure bounding box calculation is correct
2. Check `bbox_center` calculation: `((x1+x2)//2, (y1+y2)//2)`

## Dependencies

```
opencv-python >= 4.5.0
mediapipe >= 0.8.0
scikit-learn >= 1.0.0
joblib >= 1.0.0
numpy >= 1.20.0
pandas >= 1.3.0
```

## Future Enhancements

- [ ] Support for single-hand spells
- [ ] Spell combinations (sequence recognition)
- [ ] Custom PNG overlay support
- [ ] Particle system for more complex effects
- [ ] Audio feedback for spell triggers
- [ ] Recording spell sequences
- [ ] Difficulty levels (easy/hard gesture detection)

## Technical Notes

### Coordinate System

- All positions use OpenCV convention: (x, y) in pixels
- x: horizontal (0 = left, width = right)
- y: vertical (0 = top, height = bottom)
- Origin: top-left corner

### Alpha Blending Formula

```
output = (overlay * alpha) + (frame * (1 - alpha))
```

### VFX Timer

- Each effect starts with `duration` frames remaining
- Decrements by 1 per frame
- Alpha calculated as: `remaining_duration / total_duration`
- Auto-deactivates when duration reaches 0

---

**Author**: SpellMaster VFX System  
**Version**: 1.0  
**Last Updated**: March 2026
