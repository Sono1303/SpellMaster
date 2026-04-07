# Gesture Data Collection & Normalization

Welcome to the gesture data collection system with normalization support!

## Quick Start (30 seconds)

### 1️⃣ Normal Collection
```bash
python data_collector.py
```
- Press `N` for new gesture label
- Press `S` to start recording
- Press `Q` to quit
- Files saved to: `csv/{label}_{num}.csv`

### 2️⃣ Compare Mode (See Normalized vs Raw)
```bash
python data_collector.py --compare
```
- Same controls as Normal mode
- **2 CSV files** saved per recording:
  - `compare/normalize_data/{label}/normalized_{n}.csv`
  - `compare/normalize_data/{label}/raw_{n}.csv`
- Plus: `compare/normalize_data/{label}/images_{n}/frame_001.jpg`

### 3️⃣ Analyze Normalization
```bash
python compare_normalize_data.py Tiger 1
```
- Compare normalized vs raw coordinates
- Validate transformations
- Generate statistics report

---

## 📚 Documentation Files

| File | Content |
|------|---------|
| **NORMALIZE_QUICK_REFERENCE.md** | ⚡ Fast lookup table (start here!) |
| **NORMALIZE_DOCUMENTATION.md** | 📖 Detailed technical reference |
| **IMPLEMENTATION_SUMMARY.md** | 🔧 Code changes & architecture |
| **this README** | 🚀 Quick start guide |

---

## 🎯 What Gets Normalized?

### The 5 Normalization Steps

```
Raw Landmarks (from MediaPipe)
        ↓
   ┌──────────────────────────────────────────┐
   │ 1. SMOOTHING (EMA) - Reduce jitter       │
   │    α = 0.3 × current + 0.7 × previous   │
   └──────────────────────────┬───────────────┘
                              ↓
        ┌─────────────────────────────────────┬──────────────────────────┐
        │ 2. TRANSLATION                      │ 3. VALIDATION            │
        │    relative = point - left_wrist    │    ✓ Exactly 2 hands     │
        │                                     │    ✓ Stable detection    │
        │ 4. SCALING                          │    ✓ Left hand present   │
        │    normalized = relative / palm_size│    ✓ No division by 0    │
        └────────────────┬────────────────────┴──────────────────────────┘
                         ↓
            NORMALIZED DATA (ready for ML)
```

### In Plain English

1. **Smoothing**: Reduce camera/hand tremor noise
2. **Translation**: Make all coordinates relative to left wrist (0,0)
3. **Scaling**: Divide by hand size so same gesture = same data
4. **Validation**: Only keep frames with stable 2-hand detection
5. **Result**: Gesture representation that's size-invariant, position-invariant, smooth

---

## 🎮 Keyboard Controls

| Key | Action |
|-----|--------|
| `S` | Start/Stop Recording |
| `N` | New Gesture Label |
| `+` / `-` | Adjust smoothing (0.0-1.0) |
| `P` | Pause/Resume auto-record countdown |
| `Q` | Quit |

---

## 📊 Output Comparison

### What's in Each CSV?

```
normalized_1.csv:
[Label, x1_L, y1_L, x2_L, y2_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
         └ Always (0,0) in normalized     └ Relative to left wrist (not right wrist)

raw_1.csv:
[Label, x1_L, y1_L, x2_L, y2_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
         └ Varies (0.3-0.7 range)         └ Also absolute position
```

### Expected Differences

| Aspect | Normalized | Raw |
|--------|---|---|
| Left wrist (x1_L, y1_L) | Always (0, 0) ✓ | Varies by position |
| Coordinate range | Small (~-1 to +1) | Large (~0 to 1) |
| Hand-to-hand distance | Consistent | Varies with position |
| Use case | ML models | Debugging/validation |

---

## 🔍 Compare Mode Workflow

### Step 1: Collect Data
```bash
python data_collector.py --compare
```
Records gesture 2 ways simultaneously

### Step 2: Output Structure
```
data/compare/normalize_data/Tiger/
├── normalized_1.csv    ← Normalized coordinates
├── raw_1.csv          ← Raw coordinates
└── images_1/
    └── frame_001.jpg  ← Frame snapshot
```

### Step 3: Analyze
```bash
python compare_normalize_data.py Tiger 1
```

Output:
```
✅ Left wrist always at (0, 0) - Translation working correctly
✅ Scaling working correctly (normalized is compressed by factor ~18.5x)
✅ Wrist-to-wrist distance stable in normalized (std: 0.0234)
```

---

## 💻 Requirements

```bash
pip install opencv-python mediapipe pandas numpy
```

---

## 📈 Performance Metrics

### Collection Quality
- **Skipped frames < 10%**: ✅ Good
- **Skipped frames 10-30%**: ⚠️ Acceptable  
- **Skipped frames > 30%**: ❌ Poor (adjust lighting/distance)

### Validation Checks
Using `compare_normalize_data.py` automatically checks:
- [ ] Left wrist at (0, 0) in normalized
- [ ] Scaling applied (range smaller than raw)
- [ ] Hand-to-hand distance preserved
- [ ] No coordinate outliers

---

## 🎓 Educational Use

Perfect for teaching/understanding:
- Coordinate transformations
- Gesture normalization techniques
- MediaPipe hand tracking
- EMA smoothing algorithms
- Data preprocessing for ML

**See**: `NORMALIZE_DOCUMENTATION.md` for detailed explanations with formulas

---

## ❓ Troubleshooting

### ❌ High Skipped Frame Count?
- **Cause**: Poor hand detection
- **Fix**: Better lighting, stable hand position, reduce hand occlusion

### ❌ Coordinates Look Wrong?
- **Check**: Load `NORMALIZE_QUICK_REFERENCE.md` for value ranges
- **Check**: Run `compare_normalize_data.py` for validation report

### ❌ Compare Mode Not Working?
- **Check**: Folder `data/compare/normalize_data/` was created?
- **Check**: Write permissions to `data/` folder?

---

## 🚀 Integration with Training

The normalized CSV data is ready for:
- Machine learning classification models
- Gesture recognition systems  
- Hand pose estimation
- And more!

Example: Load normalized data for inference
```python
df = pd.read_csv('normalized_1.csv')
X = df.drop('Label', axis=1).values  # 85 columns of normalized coords
y = df['Label'].values               # Gesture labels
```

---

## 📞 Support

Refer to documentation files:
1. **Quick Reference** → `NORMALIZE_QUICK_REFERENCE.md`
2. **Full Details** → `NORMALIZE_DOCUMENTATION.md`
3. **Code Changes** → `IMPLEMENTATION_SUMMARY.md`

---

## ✨ Feature Highlights

✅ **Dual Mode**: Normal (fast) or Compare (validation)  
✅ **5-Step Normalization**: Translation + Scaling + Smoothing + Validation  
✅ **Auto Analysis**: Built-in comparison script with statistics  
✅ **Quality Metrics**: Skipped frame counter for detection stability  
✅ **Documentation**: 3 guides + inline code comments  
✅ **Clean Code**: Refactored for maintainability  

---

**Happy capturing! 🎉**
