# Quick Reference: Normalization Techniques

## What Gets Normalized?

| Step | Formula | Effect | Code Location |
|------|---------|--------|---|
| **Translation** | `rel = landmark - left_wrist` | All points relative to wrist | Lines 225-226 |
| **Scaling** | `norm = rel / palm_size` | Size-invariant coordinates | Lines 227-228 |
| **Smoothing** | `smooth = 0.3×curr + 0.7×prev` | Reduces jitter | Lines 116-118 |
| **Validation** | Require 2 hands, stable count | Quality control | Lines 173-180 |

---

## Original vs Normalized Comparison

### Original (Raw)
```python
# Lines 256-284: process_frame_data_raw()
# Input: MediaPipe landmarks (0.0-1.0)
# Output: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]

Example values (arbitrary screen position):
Left wrist:           (0.45, 0.50)
Left thumb:           (0.48, 0.45)
Right wrist:          (0.55, 0.52)
→ CSV: 0.45, 0.50, 0.48, 0.45, ..., 0.55, 0.52, ...
→ Position depends on camera/gesture location
```

### Normalized
```python
# Lines 230-254: process_frame_data_normalized()
# Input: MediaPipe landmarks transformed to global coordinate system
# Output: [Label, x1_L, y1_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]

Same gesture:
Left wrist (origin):  (0, 0)               # Always 0,0
Left thumb:           (0.03, -0.05)        # Relative to wrist
Right wrist:          (0.10, 0.02)         # Relative to LEFT wrist!
→ CSV: 0, 0, 0.03, -0.05, ..., 0.10, 0.02, ...
→ Position-independent (same anywhere on screen)
→ Hand-to-hand distance preserved
```

---

## How to Use Compare Mode

### Command
```bash
python data_collector.py --compare
```

### What It Does
1. Collects **both** normalized and raw data simultaneously
2. Saves **2 CSV files** per recording:
   - `normalized_{n}.csv` - With translation + scaling
   - `raw_{n}.csv` - Smoothed only (no transformation)
3. Saves **1 image** - First frame with landmarks drawn

### Output Location
```
data/compare/normalize_data/
└── Tiger/
    ├── normalized_1.csv      ← Normalized coordinates
    ├── raw_1.csv             ← Raw (smoothed) coordinates
    └── images_1/
        └── frame_001.jpg     ← Frame snapshot
```

### Why Use It?
- ✓ Validate normalization math
- ✓ Visually compare coordinate differences
- ✓ Debug if normalization is working correctly
- ✓ Create before/after analysis plots

---

## Normalization Methods Used

### 1. **Global Coordinate System**
- **Reference**: Left wrist (Landmark 0)
- **Applied to**: All 42 landmarks (both hands)
- **Function**: `_process_landmarks_with_smoothing()` -> Lines 183-186
- **Code**: Both hands use `left_wrist_x, left_wrist_y` as (0, 0)

### 2. **Relative Translation**
- **Formula**: `rel_x = landmark_x - left_wrist_x`
- **Function**: `_create_coordinate_row()` -> Lines 225-226
- **Effect**: Location-independent gesture representation

### 3. **Palm Size Normalization**
- **Formula**: `norm = rel / palm_size` where `palm_size = dist(wrist→mcp)`
- **Function**: Lines 227-228 in `_create_coordinate_row()`
- **Effect**: Size-independent gesture representation
- **Validation**: Lines 185-186 (min 0.001 to prevent division by zero)

### 4. **Exponential Moving Average Smoothing**
- **Formula**: `smooth = α × current + (1-α) × previous` (α = 0.3)
- **Function**: `apply_strong_smoothing()` -> Lines 116-118
- **Effect**: Reduces sensor noise and hand tremor

### 5. **Stability Filtering**
- **Checks**: Only accept frames with exactly 2 hands
- **Checks**: Validate hand count doesn't flicker
- **Checks**: Ensure left hand (reference) always present
- **Function**: `is_hand_count_stable()` -> Lines 79-92
- **Effect**: High-quality, consistent data collection

---

## Functions Comparison

### For Normalized Data
```python
process_frame_data_normalized(results, label)
├── _process_landmarks_with_smoothing()  # Common extract + smooth
└── _create_coordinate_row(..., normalize=True)  # Apply transform
    ├── Translation: rel_x = lx - left_wrist_x
    └── Scaling: norm_x = rel_x / palm_size
→ Returns 85-column row with transformed coordinates
```

### For Raw Data  
```python
process_frame_data_raw(results, label)
├── _process_landmarks_with_smoothing()  # Common extract + smooth
└── _create_coordinate_row(..., normalize=False)  # Keep original
    ├── No translation
    └── No scaling
→ Returns 85-column row with smoothed coordinates
```

---

## Performance & Quality Metrics

### In Data Collector
- **Frame count**: 0-200 per recording
- **Skipped frames**: Shown in console (hand detection instability)
- **Smoothing factor**: 0.6 default (configurable with +/- keys)

### Expected Results
- **Skipped frames < 10%**: Good capture quality
- **Skipped frames > 30%**: Poor lighting or hand position

---

## Integration with Training

The normalized data is ready for:
- ✓ Gesture classification models
- ✓ Gesture recognition neural networks
- ✓ Comparative gesture analysis
- ✓ Hand tracking applications

Both normalized and raw versions allow you to:
- Compare which representation works better for your use case
- Validate that normalization improves gesture ML model accuracy
