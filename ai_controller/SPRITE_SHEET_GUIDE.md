# Sprite Sheet VFX Integration Guide

## Overview

The enhanced VFX library now supports sprite sheet animations with automatic frame extraction, frame skipping for animation speed control, and advanced alpha blending for seamless visual effects.

## Key Components

### 1. `extract_sprites(image_path, rows, cols)`

Automatically extract individual frames from a sprite sheet.

**Parameters:**

- `image_path`: Path to PNG file (supports transparency)
- `rows`: Number of rows in sprite grid
- `cols`: Number of columns in sprite grid

**Returns:** List of sprite frames (NumPy arrays with BGRA format)

**Example:**

```python
from vfx_library import extract_sprites

# Extract 16 frames from a 4x4 sprite sheet
sprites = extract_sprites('assets/fireball.png', 4, 4)

# Now sprites is a list with 16 frames
print(f"Extracted {len(sprites)} frames")
```

### 2. `SpriteEffect` Class

Animated sprite effect with frame skipping and fade-out.

**Parameters:**

- `sprite_frames`: List of sprite frames
- `duration`: Total effect duration in frames
- `frame_skip`: Animation speed (1=normal, 2=half speed, 3=third speed)
- `scale`: Size multiplier (0.5=half size, 1.0=normal, 2.0=double)

**Example:**

```python
from vfx_library import extract_sprites, SpriteEffect, VFXManager

# Load sprite sheet
fireball_sprites = extract_sprites('fireball.png', 4, 4)

# Create sprite effect (plays at half speed)
fireball_effect = SpriteEffect(
    sprite_frames=fireball_sprites,
    duration=60,      # 2 seconds at 30fps
    frame_skip=2,     # Play animation twice per second
    scale=1.5         # Scale up by 50%
)

# Trigger the effect
fireball_effect.trigger()

# In your render loop:
frame = np.zeros((720, 1280, 3), dtype=np.uint8)
fireball_effect.update()
fireball_effect.draw(frame, center=(640, 360))
```

### 3. `overlay_sprite_with_alpha(frame, sprite, center, alpha)`

Advanced alpha blending for sprite overlays with proper centering.

**Parameters:**

- `frame`: Video frame (BGR)
- `sprite`: Sprite image with alpha channel (BGRA)
- `center`: Center position (x, y)
- `alpha`: Overall opacity (0.0-1.0)

**Features:**

- Centers sprite at given coordinates
- Handles off-screen boundaries gracefully
- Preserves alpha channel information
- Correct color blending

## Sprite Sheet Format

### Requirements

- **Format**: PNG with transparency (RGBA/BGRA)
- **Grid**: Regular grid layout (equal-sized frames)
- **Size**: Each frame = `total_width / cols` × `total_height / rows`

### Example: 4x4 Sprite Sheet

```
Animation frames arranged in 4 rows, 4 columns:
┌─────┬─────┬─────┬─────┐
│  0  │  1  │  2  │  3  │  Row 0
├─────┼─────┼─────┼─────┤
│  4  │  5  │  6  │  7  │  Row 1
├─────┼─────┼─────┼─────┤
│  8  │  9  │ 10  │ 11  │  Row 2
├─────┼─────┼─────┼─────┤
│ 12  │ 13  │ 14  │ 15  │  Row 3
└─────┴─────┴─────┴─────┘
```

Frames are extracted left-to-right, top-to-bottom.

## Frame Skipping for Animation Speed

The `frame_skip` parameter controls animation playback speed.

| frame_skip | Behavior                             | Use Case               |
| ---------- | ------------------------------------ | ---------------------- |
| 1          | Show new frame every webcam frame    | Fast animations        |
| 2          | Show new frame every 2 webcam frames | Normal speed           |
| 3          | Show new frame every 3 webcam frames | Slow, dramatic effects |
| 4+         | Very slow animations                 | Slow-motion effects    |

**Example:**

```python
# Normal speed (assuming 30 FPS):
SpriteEffect(sprites, frame_skip=1)  # ~30 animation frames/sec

# Slower speed:
SpriteEffect(sprites, frame_skip=2)  # ~15 animation frames/sec

# Slow motion:
SpriteEffect(sprites, frame_skip=3)  # ~10 animation frames/sec
```

## Alpha Blending Details

The sprite overlay uses advanced alpha compositing:

```
Output = (Sprite × SpriteAlpha × OverallAlpha) + (Frame × (1 - SpriteAlpha × OverallAlpha))
```

**Advantages:**

- ✅ Preserves per-pixel transparency
- ✅ Smooth blending with video background
- ✅ No harsh edges or black borders
- ✅ Handles semi-transparent pixels correctly
- ✅ Graceful fade-out effect

## Integration with Spell Recognizer

To use sprite effects with the spell recognizer:

```python
from vfx_library import extract_sprites, SpriteEffect, VFXManager

# Load sprite sheets
tiger_sprites = extract_sprites('assets/tiger_fireball.png', 4, 4)
dragon_sprites = extract_sprites('assets/dragon_ice.png', 4, 4)
ox_sprites = extract_sprites('assets/ox_lightning.png', 4, 4)

# In VFXManager initialization, replace built-in effects:
vfx_manager.effects['Tiger'] = SpriteEffect(tiger_sprites, duration=60, frame_skip=2)
vfx_manager.effects['Dragon'] = SpriteEffect(dragon_sprites, duration=60, frame_skip=2)
vfx_manager.effects['Ox'] = SpriteEffect(ox_sprites, duration=60, frame_skip=2)
```

## Performance Considerations

### Memory Usage

- Each sprite frame is stored in memory
- 16 frames (4×4) at 1280×720: ~15MB per effect
- 3 effects: ~45MB total

### CPU Usage

- Sprite extraction is one-time cost (~10ms per sheet)
- Rendering: ~2-3ms per effect (depending on sprite size)
- Alpha blending: Highly optimized with NumPy

### Optimization Tips

1. **Use smaller sprite sizes** (256×256 instead of 512×512)
2. **Increase frame_skip** to reduce animation computations
3. **Reduce sprite scale** when far from camera
4. **Use max_num_hands=1** if not detecting dual-hand gestures

## Troubleshooting

### Issue: Sprites have black background

**Solution:** Ensure your PNG files have a transparent background (RGBA).

```bash
# Convert with ImageMagick:
convert input.png -transparent black output.png
```

### Issue: Animation plays too fast

**Solution:** Increase `frame_skip` parameter.

```python
SpriteEffect(sprites, frame_skip=3)  # Slower
```

### Issue: Sprites don't blend smoothly

**Solution:** Check that sprite PNG preserves alpha channel.

```python
import cv2
img = cv2.imread('sprite.png', cv2.IMREAD_UNCHANGED)
print(f"Channels: {img.shape[2]}")  # Should be 4 (BGRA)
```

## Advanced Usage

### Semi-transparent Sprites

Sprites with semi-transparent pixels (not fully opaque) will blend correctly:

```python
# Sprite with 50% transparency will blend at 50% intensity
overlay_sprite_with_alpha(frame, sprite, center, alpha=1.0)
```

### Scaling Sprites Dynamically

Adjust sprite size based on distance or intensity:

```python
# Small effect
effect = SpriteEffect(sprites, scale=0.5)

# Large effect
effect = SpriteEffect(sprites, scale=2.0)

# Dynamic scaling
effect = SpriteEffect(sprites, scale=1.0 + confidence / 100)
```

### Custom Animation Speed per Spell

```python
# Fast spell
tiger_effect = SpriteEffect(tiger_sprites, frame_skip=1)

# Medium spell
dragon_effect = SpriteEffect(dragon_sprites, frame_skip=2)

# Slow, powerful spell
ox_effect = SpriteEffect(ox_sprites, frame_skip=3)
```

## Example: Complete Sprite Sheet Setup

```python
from vfx_library import extract_sprites, SpriteEffect, VFXManager

# Create VFX manager
vfx_manager = VFXManager()

# Load and setup sprite effects
try:
    # Load sprite sheets (4x4 grids)
    tiger_sprites = extract_sprites('assets/fireball_4x4.png', 4, 4)
    dragon_sprites = extract_sprites('assets/ice_4x4.png', 4, 4)
    ox_sprites = extract_sprites('assets/lightning_4x4.png', 4, 4)

    # Create sprite effects with custom parameters
    vfx_manager.effects['Tiger'] = SpriteEffect(
        tiger_sprites,
        duration=60,    # 2 seconds
        frame_skip=2,   # Normal speed
        scale=1.5       # 50% larger
    )

    vfx_manager.effects['Dragon'] = SpriteEffect(
        dragon_sprites,
        duration=60,
        frame_skip=2,
        scale=1.5
    )

    vfx_manager.effects['Ox'] = SpriteEffect(
        ox_sprites,
        duration=60,
        frame_skip=2,
        scale=1.5
    )

    print("✓ Sprite effects loaded successfully")

except Exception as e:
    print(f"✗ Error loading sprite sheets: {e}")
    print("  Falling back to procedural effects")
```

## References

- **Alpha Blending**: https://en.wikipedia.org/wiki/Alpha_compositing
- **Sprite Sheets**: https://en.wikipedia.org/wiki/Sprite_(computer_graphics)
- **OpenCV Docs**: https://docs.opencv.org/

---

**Version**: 2.0 with Sprite Sheet Support  
**Last Updated**: March 2026
