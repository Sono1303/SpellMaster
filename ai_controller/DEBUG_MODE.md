# Debug Mode Guide - Spell Recognizer

## Quick Start

Run the spell recognizer:

```powershell
python SpellMaster\ai_controller\spell_recognizer.py
```

## Enabling Debug Mode

1. **Press `D`** on your keyboard while the application is running
2. You'll see on-screen confirmation: `🔧 Debug Mode: ON`
3. The debug center point (cyan circle) appears at screen center

## Casting Spells in Debug Mode

| Key   | Spell             | VFX Effect                           |
| ----- | ----------------- | ------------------------------------ |
| **1** | Fireball (Tiger)  | Red→Orange→Yellow circles with glow  |
| **2** | Ice (Dragon)      | Cyan overlay with diamond ice shards |
| **3** | Lightning (Ox)    | White & cyan zigzag lightning bolts  |
| **D** | Toggle Debug Mode | Turn debug mode OFF                  |

## On-Screen Display

### Debug Mode Active

- **Orange text**: `DEBUG MODE: ON`
- **Cyan circle**: Effect center point
- **Debug help**: Lists all available spell keys

### Console Output

When you cast a spell in debug mode:

```
✨ Tiger spell cast! (VFX: Tiger)
✨ Dragon spell cast! (VFX: Dragon)
✨ Ox spell cast! (VFX: Ox)
```

## Features

✅ **Keyboard Spell Casting** - No gesture recognition required  
✅ **Visual Feedback** - On-screen UI shows debug mode status  
✅ **Effect Preview** - Test all VFX effects independently  
✅ **Console Logging** - All spell casts logged to terminal  
✅ **Easy Toggle** - Press D to enable/disable instantly

## Example Workflow

1. Launch app: `python spell_recognizer.py`
2. Press `D` to enable debug mode
3. Press `1` to see Fireball effect
4. Press `2` to see Ice effect
5. Press `3` to see Lightning effect
6. Press `D` to disable debug mode
7. Press `Q` to quit

## Technical Details

- **Debug Center**: Hardcoded to screen center (640, 360) by default
- **Effect Duration**: 30 frames (same as gesture-triggered)
- **Visual Feedback**: Cyan crosshair at effect center
- **No Gesture Required**: Bypasses MediaPipe completely when in debug mode

## Troubleshooting

**Q: Debug mode won't activate?**  
A: Make sure the OpenCV window is active (focused) when pressing D

**Q: Spells not appearing?**  
A: Check that the VFX effects are rendering (watch for console messages)

**Q: Wrong spell casting?**  
A: Check you pressed the correct number (1, 2, or 3)

---

**Version**: 1.0  
**Status**: Ready for testing
