# 🎮 SpellMaster - Gesture-Based Spell Combat Game

Defend your statue using **hand gesture spells**! A unique real-time spell-casting game powered by hand recognition AI.

---

## 🚀 Quick Start

### Install & Run
```bash
cd e:\SpellMaster
pip install -r requirements.txt
python start_all.py
```

Launches 3 components:
- **Gesture Server**: Webcam hand detection (port 5555)
- **Game**: Pygame window (port 6666)  
- **Gesture Client**: UDP bridge

---

## 🎮 How to Play

### Game States

| State | Action | Result |
|-------|--------|--------|
| **Start** | Hold any gesture 1s, release | Game begins |
| **Playing** | Perform gestures to cast spells | Defend statue! |
| **Wave Break** | Wait (monsters defeated) | Next wave coming |
| **Game Over** | Hold gesture 1s to restart | Wave 1 starts (reset) |
| **Victory** | Survive all 5 waves! | 🎉 Win! |

### Casting Spells

1. **Position hand** in front of webcam (30-100cm distance)
2. **Make gesture shape** matching the spell
3. **Hold steady** for ~1 second (progress shown in server window)
4. **Release** → Spell fires at nearest monster ✨

### Spell Gestures

| Gesture | Spell | Effect |
|---------|-------|--------|
| 🔥 | Fire | High damage, single target |
| ❄️ | Ice | Freeze enemy |
| ⚡ | Lightning | Chain damage |
| 💧 | Water | Healing |
| 🪨 | Earth | AOE damage |
| 💨 | Air | Knockback |
| ✨ | Light | Support/buff |
| 🌑 | Dark | Debuff/curse |
| 💎 | Crystal | Special effect |
| 🔮 | Phoenix | Ultimate (unlock via kills) |

---

## ⌨️ Controls

### Keyboard (Fallback)
- `1-0` or `Mouse`: Select & cast spells
- `Q`: Quit

### Hand Gestures (Recommended)
- Make hand shape → hold 1s → release → cast!

---

## 📊 Game Info

### Health
- **Player**: 100 HP
- **Statue**: 150 HP ← Main target to defend
- **Either = 0**: Game Over

### Waves
- **Total**: 5 waves
- **Difficulty**: Increases each wave
- **Monsters spawn**: Every 3 seconds per wave
- **Wave transition**: 3-second break between waves
- **Clear condition**: Defeat all monsters in wave

### Spells
- **Cooldown**: Each spell has cooldown after cast
- **Mana**: Some spells use mana (regenerates)
- **Targeting**: Hits nearest live monster
- **Special**: Some unlock after kill milestones

---

## 🐛 Quick Fixes

| Problem | Fix |
|---------|-----|
| No hand detected | Better lighting, move closer (30-100cm) |
| Spell not casting | Check monsters on screen, right confidence |
| Game crashes | Close other webcam apps, Python 3.11+ |
| Gesture weak | Better lighting, steadier hand, clearer shape |
| Statue HP stuck | Restart game with gesture |

---

## 💡 Tips

- **Best practice**: Steady hand, full hand shape, good lighting
- **Strategy**: Use Air to knockback threats away from statue
- **Lighting**: Shadows = bad detection accuracy
- **Position**: Move away from monsters when safe
- **Consistent**: Practice your best gestures regularly

---

## ⚙️ Advanced Config

### Gesture Confidence (stricter detection)
Edit `ai_controller/spell_recognizer.py`:
```python
self.confidence_threshold = 0.85  # 0.0-1.0 (higher = stricter)
```

### Gesture Hold Time
Edit `ai_controller/gesture_server.py`:
```python
self.gesture_hold_duration = 1.0  # seconds
```

---

**Version**: 1.0 | April 2026  
**Tech**: MediaPipe + Pygame + scikit-learn  
**Network**: UDP (5555 ↔ 6666)  
**Good luck, Wizard!** ✨
