# Quick Integration: Using Sprite Sheets with Spell Recognizer

## File Structure for Sprite Assets

```
SpellMaster/
├── ai_controller/
│   ├── spell_recognizer.py       # Main recognizer
│   ├── vfx_library.py            # Enhanced VFX with sprites
│   ├── assets/
│   │   └── sprites/
│   │       ├── fireball.png      # 4x4 sprite sheet (Tiger)
│   │       ├── ice.png           # 4x4 sprite sheet (Dragon)
│   │       └── lightning.png     # 4x4 sprite sheet (Ox)
│   └── ...
```

## Integration Steps

### Step 1: Prepare Sprite Sheets

- **Format**: PNG with transparent background (RGBA)
- **Grid**: Regular grid (e.g., 4×4 = 16 frames)
- **Size**: Recommended 256×256 to 512×512 per frame
- **Transparency**: All non-sprite areas must be transparent

### Step 2: Add Sprite Loading to spell_recognizer.py

In the `SpellRecognizer.__init__()` method, after VFX manager creation:

```python
# After: self.vfx_manager = VFXManager()

from vfx_library import extract_sprites, SpriteEffect

# Optional: Load sprite sheets if available
sprites_dir = Path(__file__).parent / "assets" / "sprites"

try:
    # Load sprite sheets
    tiger_sprites = extract_sprites(
        str(sprites_dir / "fireball.png"),
        rows=4,
        cols=4
    )
    if tiger_sprites:
        self.vfx_manager.effects['Tiger'] = SpriteEffect(
            tiger_sprites,
            duration=60,
            frame_skip=2,
            scale=1.5
        )

    # Repeat for Dragon and Ox...
    dragon_sprites = extract_sprites(
        str(sprites_dir / "ice.png"),
        rows=4,
        cols=4
    )
    if dragon_sprites:
        self.vfx_manager.effects['Dragon'] = SpriteEffect(
            dragon_sprites,
            duration=60,
            frame_skip=2,
            scale=1.5
        )

    ox_sprites = extract_sprites(
        str(sprites_dir / "lightning.png"),
        rows=4,
        cols=4
    )
    if ox_sprites:
        self.vfx_manager.effects['Ox'] = SpriteEffect(
            ox_sprites,
            duration=60,
            frame_skip=2,
            scale=1.5
        )

except Exception as e:
    print(f"Warning: Could not load sprite sheets: {e}")
    print("Using procedural effects instead")
```

### Step 3: No Changes Needed!

The rest of `spell_recognizer.py` works automatically with sprite effects. The VFX rendering pipeline is identical regardless of whether you use procedural or sprite-based effects.

## Adjusting Animation Speed

Modify `frame_skip` parameter:

```python
# Fast animation (every frame)
SpriteEffect(sprites, frame_skip=1)

# Normal speed (every 2 frames)
SpriteEffect(sprites, frame_skip=2)

# Slow motion (every 3 frames)
SpriteEffect(sprites, frame_skip=3)
```

## Adjusting Sprite Size

Modify `scale` parameter:

```python
# Half size
SpriteEffect(sprites, scale=0.5)

# Normal size
SpriteEffect(sprites, scale=1.0)

# Double size
SpriteEffect(sprites, scale=2.0)
```

## Creating Sprite Sheets

### Using GIMP

1. Create/import your animation frames
2. Create a new image: 256×256 pixels (for 4×4 grid of 64×64 frames)
3. Place frames in a 4×4 grid layout
4. Export as PNG with transparency: `fireball.png`

### Using Python (PIL/Pillow)

```python
from PIL import Image

# Create 4x4 grid (1024×1024 image with 256×256 frames)
sheet = Image.new('RGBA', (1024, 1024), (0, 0, 0, 0))

frames = [...]  # Your PIL Image objects
for i, frame in enumerate(frames):
    row = i // 4
    col = i % 4
    x = col * 256
    y = row * 256
    sheet.paste(frame, (x, y), frame if frame.mode == 'RGBA' else None)

sheet.save('fireball.png')
```

### Using ImageMagick

```bash
# Combine images into a 4x4 grid
montage frame_0*.png -tile 4x4 -geometry 64x64+0+0 fireball.png

# Ensure transparency
convert fireball.png -background transparent -alpha on fireball_transparent.png
```

## Testing Without Real Sprites

Run the sprite example to test with procedural effects:

```powershell
cd SpellMaster
python ai_controller\sprite_example.py
```

Controls:

- **1**: Fireball
- **2**: Ice
- **3**: Lightning
- **Q**: Quit

## Performance Tips

| Setting     | Impact          | Recommendation                   |
| ----------- | --------------- | -------------------------------- |
| Sprite Size | Memory & Speed  | Use 256×256 frames               |
| Frame Skip  | Animation Speed | 2 = Normal, 1 = Fast             |
| Scale       | Quality         | 1.0 = Crisp, >2.0 = Pixelated    |
| Grid Size   | Frame Count     | 4×4 = 16 frames, 5×5 = 25 frames |

## Troubleshooting

| Problem             | Solution                                       |
| ------------------- | ---------------------------------------------- |
| Sprites not showing | Check file exists at `assets/sprites/`         |
| Black background    | Use PNG with transparency (RGBA)               |
| Animation too fast  | Increase `frame_skip` to 3 or 4                |
| Animation too slow  | Decrease `frame_skip` to 1                     |
| Low FPS             | Reduce sprite size or disable multiple effects |

## Key Functions Reference

```python
# Extract sprites
from vfx_library import extract_sprites
sprites = extract_sprites('sprite.png', rows=4, cols=4)

# Create sprite effect
from vfx_library import SpriteEffect
effect = SpriteEffect(sprites, duration=60, frame_skip=2, scale=1.5)

# Overlay sprite (advanced)
from vfx_library import overlay_sprite_with_alpha
overlay_sprite_with_alpha(frame, sprite, center=(640, 360), alpha=0.8)
```

## Complete Integration Example

See `sprite_example.py` for a complete working example:

```bash
python ai_controller\sprite_example.py
```

---

**Quick Start**: Place sprite sheets in `assets/sprites/` and uncomment the sprite loading code in `spell_recognizer.py`. That's it!
