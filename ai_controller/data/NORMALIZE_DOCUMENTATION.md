# Gesture Data Collection - Normalization Documentation

## Overview

The `data_collector.py` module provides two modes for collecting two-hand gesture data:
1. **NORMAL MODE**: Collect normalized data only
2. **COMPARE MODE**: Collect both normalized and raw (smoothed-only) data side-by-side for validation

---

## Quick Start

### Normal Mode (Default)
```bash
python data_collector.py
```
- Output: `data/csv/{label}_{num}.csv`
- Normalized coordinates only

### Compare Mode
```bash
python data_collector.py --compare
```
- Output: `data/compare/normalize_data/{label}/{normalized,raw}_{num}.csv`
- Both normalized and raw data
- 2 CSV files + 1 image per recording

---

## Normalization Techniques

### 1. **Global Coordinate Reference** (Right Hand Relative to Left)

**Purpose**: Preserve hand-to-hand spatial relationships (gesture shape/volume)

**Method**:
- Left hand wrist (Landmark 0) = **global origin (0, 0)**
- All 21 landmarks of left hand transformed relative to its wrist
- All 21 landmarks of right hand **also** transformed relative to **left** wrist (not right wrist)

**Benefits**:
- ✓ Gesture location-invariant (position on screen doesn't matter)
- ✓ Hand-to-hand distance preserved (important for two-hand gestures)
- ✓ Single unified coordinate system for both hands

**Code Location**: `process_frame_data_normalized()` [Lines 230-254]

```python
# Lines 243-246: Right hand uses LEFT wrist as reference
rel_x = lx - left_wrist_x      # Relative to LEFT wrist (NOT right wrist)
rel_y = ly - left_wrist_y      # Relative to LEFT wrist
norm_x = rel_x / left_palm_size
norm_y = rel_y / left_palm_size
```

---

### 2. **Translation Transformation**

**Purpose**: Calculate relative position instead of absolute coordinates

**Formula**:
```
rel_x = landmark_x - left_wrist_x
rel_y = landmark_y - left_wrist_y
```

**Result**: 
- Left hand wrist always at (0, 0)
- All other landmarks offset from wrist

**Example**:
```
Raw:        Normalized:
Landmark 0: (0.45, 0.50) → (0, 0)           [wrist]
Landmark 1: (0.46, 0.48) → (0.01, -0.02)    [thumb]
Landmark 5: (0.42, 0.45) → (-0.03, -0.05)   [index]
```

**Code Location**: `_create_coordinate_row()` [Lines 225-226]

---

### 3. **Scale Normalization By Palm Size**

**Purpose**: Make gestures size-invariant (gesture with large hand = same as small hand)

**Palm Size Reference**:
- Distance from **wrist (Landmark 0)** to **middle finger MCP (Landmark 9)**
- This is a stable, intrinsic hand dimension

**Formula**:
```
palm_size = √((mcp_x - wrist_x)² + (mcp_y - wrist_y)²)
if palm_size < 0.001: palm_size = 0.001  # Division-by-zero protection

norm_x = rel_x / palm_size
norm_y = rel_y / palm_size
```

**Result**:
- All coordinates divided by hand scale
- Same gesture shape produces identical values regardless of hand size

**Example**:
```
Large hand:  palm_size = 0.15 → norm_x = 0.06 / 0.15 = 0.40
Small hand:  palm_size = 0.07 → norm_x = 0.028 / 0.07 = 0.40
                                         ^ Same normalized value!
```

**Code Location**: 
- Palm size calculation: Lines 183-186
- Normalization: Lines 227-228

---

### 4. **Smoothing (Exponential Moving Average)**

**Purpose**: Reduce sensor jitter and detection noise from MediaPipe

**Method**: Exponential Moving Average (EMA)
```
smoothed = α × current + (1-α) × previous
```

**Parameters**:
- **Alpha**: 0.3 (means 30% current, 70% previous)
- **Effect**: Heavily weights previous frame (70%) for maximum stability
- **Per-hand**: Applied independently to each hand

**Stability**:
- Trades responsiveness for stability
- Jitter from hand shaking or tracking errors gets smoothed out
- Prevents single-frame detection artifacts

**Code Location**: `apply_strong_smoothing()` [Lines 99-122]

```python
# Line 116: Even stronger smoothing for overlapping hands
alpha = self.smoothing_factor * 0.5  # 0.6 * 0.5 = 0.3

# Lines 117-118: Exponential moving average per coordinate
smoothed_x = alpha * x + (1 - alpha) * prev.get(f"x{i}", x)
smoothed_y = alpha * y + (1 - alpha) * prev.get(f"y{i}", y)
```

---

### 5. **Stability Validation & Filtering**

**Purpose**: Ensure only high-quality frames are collected

**Validation Checks**:

| Check | Purpose | Code |
|-------|---------|------|
| **Hand Count == 2** | No partial detections | Lines 173-176 |
| **Hand Count Stability** | No flickering (hand appearing/disappearing) | Lines 178-180 |
| **Left Hand Present** | Ensure global reference point exists | Lines 217-220 |
| **Palm Size > 0** | Division-by-zero protection | Lines 185-186 |

**Impact**: 
- Skipped frames counter shows how many frames were filtered
- Low skipped count = stable, consistent detection
- High skipped count = detection jitter (adjust lighting/distance)

**Code Location**: `is_hand_count_stable()` [Lines 79-92]

---

## Data Output Format

### CSV Column Structure
All CSV files have 85 columns:
```
[Label, x1_L, y1_L, x2_L, y2_L, ..., x21_L, y21_L, x1_R, y1_R, ..., x21_R, y21_R]
 └────┘ └─────────────────────────────────────────┘ └──────────────────────────┘
 Label         Left Hand (42 values)                  Right Hand (42 values)
       └─────────────────────────────────────────────────────────────────────────┘
                                85 total columns
```

### Directory Structure

#### Normal Mode
```
data/
└── csv/
    ├── Tiger_1.csv      (normalized)
    ├── Tiger_2.csv      (normalized)
    └── ...
```

#### Compare Mode
```
data/
└── compare/
    └── normalize_data/
        ├── Tiger/
        │   ├── normalized_1.csv
        │   ├── raw_1.csv
        │   └── images_1/
        │       └── frame_001.jpg
        ├── Dragon/
        │   ├── normalized_1.csv
        │   ├── raw_1.csv
        │   └── images_1/
        │       └── frame_001.jpg
        └── ...
```

---

## Code Organization & Functions

### Core Processing Pipeline

```
_process_landmarks_with_smoothing()  [Lines 166-208]
    ↓
    ├─ Smoothing filter per hand
    ├─ Hand count validation
    ├─ Extract left wrist (reference)
    ├─ Calculate palm_size
    └─ Return: (left_landmarks, right_landmarks, wrist, palm_size)
    
    ├─ process_frame_data_normalized()  [Lines 230-254]
    │   └─ Translation + Scaling applied
    │
    └─ process_frame_data_raw()  [Lines 256-284]
        └─ No transformation (smoothed only)
```

### Key Functions

| Function | Purpose | Input | Output |
|----------|---------|-------|--------|
| `_process_landmarks_with_smoothing()` | Common smoothing + validation | MediaPipe results | Smoothed landmarks + reference point |
| `_create_coordinate_row()` | Generate coordinate row | Landmarks, origin, scale, normalize flag | 42-element coordinate list |
| `process_frame_data_normalized()` | Normalized data processing | MediaPipe results | 85-column CSV row |
| `process_frame_data_raw()` | Raw data processing | MediaPipe results | 85-column CSV row |
| `apply_strong_smoothing()` | EMA filterering | Coordinates | Smoothed coordinates |
| `is_hand_count_stable()` | Stability check | Hand count | Boolean (stable/unstable) |

### Comparison & Validation

**Use Compare Mode to**:
1. ✓ Understand normalization effect on gesture coordinates
2. ✓ Validate normalization formulas
3. ✓ Debug detection issues (high skipped frame count)
4. ✓ Visual inspection of gesture capture quality
5. ✓ Create comparative analysis plots/scripts

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `S` | Start/Stop Recording |
| `N` | New Gesture Label |
| `+` / `-` | Adjust smoothing factor (0.0-1.0) |
| `P` | Pause/Resume auto-record countdown |
| `Q` | Quit |

---

## Troubleshooting

### High Skipped Frame Count?
- **Cause**: Hand detection/tracking instability
- **Solution**: Better lighting, stable hand position, fewer occlusions

### Coordinates Look Strange?
- **Normalized**: Check palm_size (should be ~0.1-0.2)
- **Raw**: Check if MediaPipe is detecting hands correctly

### Compare Mode Not Working?
- **Check**: `data/compare/normalize_data/` folder created?
- **Check**: File permissions for writing to folders

---

## Code Complexity Reduction

The refactored code reduces duplication by:

1. **Shared Pipeline**: `_process_landmarks_with_smoothing()` handles both modes
2. **Parametric Processing**: `_create_coordinate_row()` with `normalize` flag
3. **Unified Recording**: Same `start_recording/stop_recording` for both modes
4. **Cleaner UI**: Simplified `draw_ui()` with mode parameter

**Lines of Code**:
- Original `process_frame_data()`: ~80 lines
- Refactored split functions: ~75 lines total (more modular)

---

## References

- MediaPipe Hand landmarks: 21 points per hand
- Global vs Local coordinates explained above
- Transform mathematics: Translation + Scaling
- Exponential Moving Average: Signal processing technique
