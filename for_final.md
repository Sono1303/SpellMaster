# Ignite: Spell Master - Final Project Report

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Data Collection](#2-data-collection)
3. [Data Preprocessing and Normalization](#3-data-preprocessing-and-normalization)
4. [Machine Learning Model](#4-machine-learning-model)
5. [Supplementary Modules](#5-supplementary-modules)
6. [Difficulties and Solutions](#6-difficulties-and-solutions)
7. [Improvements and Optimizations](#7-improvements-and-optimizations)
8. [Game Operation Guide](#8-game-operation-guide)

---

## 1. Project Overview

**Ignite: Spell Master** is a gesture-controlled tower defense game where the player casts spells by performing two-handed gestures in front of a webcam. The system consists of 2 independent processes:

- **AI Controller** (Python + OpenCV + MediaPipe + sklearn): Captures webcam, detects hand gestures, predicts spells via ML model, broadcasts via UDP
- **Pygame Game** (Python + Pygame): Receives spell events, renders game world, manages wave-based combat

**Tech Stack:**
- Python 3.11.9
- OpenCV 4.x (webcam capture, image processing)
- MediaPipe Hands (hand landmark detection)
- scikit-learn (gesture classification)
- Pygame (game engine, 1280x768 @ 60 FPS)
- UDP Socket (inter-process communication)
- joblib (model serialization)

---

## 2. Data Collection

### 2.1 Tool

Data is collected using `ai_controller/data/data_collector.py` - the `GestureDataCollector` class.

### 2.2 Process

1. The webcam captures video at 1280x720
2. MediaPipe Hands detects up to 2 hands with 21 landmarks each (x, y coordinates)
3. The system requires **exactly 2 hands** to be visible simultaneously
4. Data is recorded in real-time as the user performs gestures
5. Each recording session produces one CSV file (e.g., `Fire_1.csv`, `Fire_2.csv`, etc.)

### 2.3 MediaPipe Configuration

| Parameter | Value |
|-----------|-------|
| `static_image_mode` | `False` (video stream) |
| `model_complexity` | `1` (higher accuracy for interlaced fingers) |
| `max_num_hands` | `2` |
| `min_detection_confidence` | `0.5` |
| `min_tracking_confidence` | `0.4` |

### 2.4 Raw Data Format

Each CSV has **85 columns**:

| Column | Description |
|--------|-------------|
| `Label` | Gesture class name (e.g., "Fire", "Ice") |
| Columns 1-42 | Left hand: 21 landmarks x 2 coordinates (x, y) |
| Columns 43-84 | Right hand: 21 landmarks x 2 coordinates (x, y) |

### 2.5 Gesture Classes (10 total)

| # | Gesture | Description |
|---|---------|-------------|
| 1 | Fire | Fire spell hand sign |
| 2 | Water | Water spell hand sign |
| 3 | Earth | Earth spell hand sign |
| 4 | Air | Air spell hand sign |
| 5 | Lightning | Lightning spell hand sign |
| 6 | Ice | Ice spell hand sign |
| 7 | Dark | Dark spell hand sign |
| 8 | Light | Light spell hand sign |
| 9 | Crystal | Crystal spell hand sign (special) |
| 10 | Phoenix | Phoenix spell hand sign (special) |

### 2.6 Dataset Statistics

| Gesture | Samples | Percentage |
|---------|---------|------------|
| Ice | 3,800 | 12.0% |
| Fire | 3,599 | 11.3% |
| Dark | 3,400 | 10.7% |
| Air | 3,000 | 9.5% |
| Crystal | 3,000 | 9.5% |
| Earth | 3,000 | 9.5% |
| Lightning | 3,000 | 9.5% |
| Phoenix | 3,000 | 9.5% |
| Light | 2,987 | 9.4% |
| Water | 2,954 | 9.3% |
| **Total** | **31,740** | **100%** |

- **Files merged**: 159 CSV files
- **Imbalance ratio**: 1.29x (well-balanced)

---

## 3. Data Preprocessing and Normalization

### 3.1 Normalization Pipeline

```
Raw MediaPipe Landmarks
    |
    v
EMA Smoothing (alpha = 0.3)
    |
    v
Translation (left wrist = origin)
    |
    v
Scaling (divide by palm size)
    |
    v
84-feature vector
```

### 3.2 Steps in Detail

**Step 1 - Smoothing (EMA):**
- `smoothed = 0.3 * current + 0.7 * previous`
- Reduces frame-to-frame noise from MediaPipe detection

**Step 2 - Translation:**
- Global reference point: Left hand wrist (Landmark 0)
- `rel_x = landmark_x - left_wrist_x`
- `rel_y = landmark_y - left_wrist_y`
- Both hands use the same origin, making the feature position-invariant

**Step 3 - Scaling:**
- `palm_size = distance(wrist, middle_finger_MCP)` (Landmark 0 to Landmark 9)
- `norm_x = rel_x / palm_size`
- `norm_y = rel_y / palm_size`
- Guard: `palm_size` minimum = 0.001 to prevent division by zero
- Makes features scale-invariant (works at any distance from camera)

**Step 4 - Feature Vector:**
- 84 floats total: 21 landmarks x 2 coordinates x 2 hands
- Order: Left hand (42 values) + Right hand (42 values)

### 3.3 Data Cleaning (Merger)

Tool: `ai_controller/data/gesture_data_merger.py`

Rules applied:
1. Drop rows that are entirely NaN
2. Drop rows where all 84 coordinate columns = 0
3. Drop rows missing either hand (left or right columns all zeros)
4. Reject files without exactly 85 columns
5. Output: `final_train.csv` (single merged file)

---

## 4. Machine Learning Model

### 4.1 Model Selection (Battle)

Tool: `ai_controller/data/gesture_model_battle.py`

4 models are trained and compared using a balanced scoring system:

| Model | Architecture | Key Parameters |
|-------|-------------|----------------|
| Random Forest | 100 decision trees | `n_estimators=100`, `n_jobs=-1` |
| SVM (RBF) | Support Vector Machine, RBF kernel | `kernel='rbf'`, `probability=True` |
| KNN | K-Nearest Neighbors | `n_neighbors=5` |
| MLP Neural Network | 2-layer perceptron | `hidden_layer_sizes=(64, 32)`, `max_iter=500`, `early_stopping=True` |

### 4.2 MLP Architecture

```
Input Layer (84 features)
    |
Dense Layer 1 (64 neurons, ReLU activation)
    |
Dense Layer 2 (32 neurons, ReLU activation)
    |
Output Layer (10 classes, softmax)
```

### 4.3 Training Configuration

| Parameter | Value |
|-----------|-------|
| Train/Test Split | 80% / 20% (stratified) |
| Random State | 42 |
| Validation Fraction (MLP) | 10% |
| Early Stopping (MLP) | Enabled |

### 4.4 Evaluation Metrics

**Balanced Score Formula:**
```
balanced_score = 0.7 * accuracy + 0.3 * speed_score
speed_score = min(20 / (inference_ms + 1), 1.0)
```

### 4.5 Results

| Model | Accuracy | F1-Score | Inference Time | Balanced Score |
|-------|----------|----------|----------------|----------------|
| **SVM (RBF)** | **100.00%** | **1.0000** | **0.915 ms** | **1.0000** |
| Random Forest | 99.98% | 0.9998 | 17.231 ms | - |
| KNN | 99.97% | 0.9997 | 2.846 ms | - |
| MLP | 99.96% | 0.9996 | 0.925 ms | - |

- **Winner**: SVM (RBF) - perfect accuracy AND fastest inference
- **Training samples**: 25,392 / **Test samples**: 6,348
- **Per-class precision/recall/F1**: 1.00 for all 10 gesture classes

### 4.6 Model Output

- Serialized model: `ai_controller/data/models/best_spell_model.pkl` (joblib)
- Comparison chart: `ai_controller/data/plots/model_comparison.png`
- Confusion matrix: `ai_controller/data/plots/confusion_matrix.png`
- Statistics report: `ai_controller/data/models/model_statistics.md`

---

## 5. Supplementary Modules

### 5.1 One Euro Filter (`ai_controller/utils/one_euro_filter.py`)

**Purpose:** Reduces MediaPipe landmark jitter while preserving fast, intentional movements.

**How it works:**
- Adaptive low-pass filter that adjusts cutoff frequency based on signal speed
- When hands are **still**: Heavy smoothing (low cutoff) to eliminate jitter
- When hands **move fast**: Minimal smoothing (high cutoff) to reduce lag
- 42 independent filter instances per hand (21 landmarks x 2 axes)

**Parameters:**
| Parameter | Value | Description |
|-----------|-------|-------------|
| `freq` | 30.0 Hz | Estimated frame rate |
| `min_cutoff` | 1.0 Hz | Minimum cutoff (smoothing when still) |
| `beta` | 0.007 | Speed coefficient (responsiveness when moving) |
| `d_cutoff` | 1.0 Hz | Derivative cutoff frequency |

**Reference:** Casiez et al., "1 Euro Filter: A Simple Speed-based Low-pass Filter for Noisy Input in Interactive Systems", CHI 2012.

### 5.2 Gesture Server (`ai_controller/gesture_server.py`)

**Purpose:** UDP server managing the full gesture detection pipeline.

**Key features:**
- Dual-hand requirement: Both hands must be detected AND close together
- Bounding box collision detection for hand proximity check
- 3-state gesture system: `focus` (detected) -> `holding` (charging) -> `cast` (released after 1s)
- Broadcasts JSON payloads via UDP to port 6666

### 5.3 Gesture Client (`pygame/scripts/gesture_client.py`)

**Purpose:** UDP listener running in a daemon thread inside the game process.

**Key features:**
- Non-blocking queue-based architecture (`queue.Queue`, maxsize=100)
- Thread-safe FIFO spelling event consumption
- Socket error handling for graceful shutdown

### 5.4 Spell System (`pygame/scripts/spell.py`)

**10 spell types with unique effects:**

| Spell | Type | Damage | Mana | Special Effect |
|-------|------|--------|------|----------------|
| Fire | ST | 15 | 10 | Burn 5 dmg / 3s |
| Water | AOE | 10 | 12 | Knockup 1.0s |
| Earth | ST | 20 | 10 | Stun 1.0s |
| Air | AOE | 8 | 10 | Knockback force 150 |
| Lightning | ST | 25 | 15 | Chain to nearby enemies |
| Ice | ST | 12 | 12 | Freeze 1s + Slow 50% for 3s |
| Dark | ST | 10 | 15 | Curse spread + Burn 4 dmg / 5s |
| Light | AOE | 18 | 14 | Double hit (1s delay) |
| Crystal | AOE | 30 | 20 | Kill bonus redistribution (locked, requires 10 kills) |
| Phoenix | AOE | 35 | 25 | Delayed explosion (locked, requires 10 kills) |

ST = Single Target, AOE = Area of Effect

### 5.5 Wave System (`pygame/scripts/main_pygame.py`)

- Auto-scales from `pygame/data/level_config.json`
- 7 waves with increasing difficulty
- Each wave defines monster types, portal assignments, spawn delays
- Wave countdown between waves
- Victory detection when all waves cleared + all monsters dead

### 5.6 Entity System (`pygame/scripts/entity.py`)

**8 monster types:**

| Monster | HP | Damage | Speed |
|---------|----|--------|-------|
| Slime | 15 | 5 | 35 |
| Skeleton | 20 | 8 | 70 |
| Orc | 30 | 10 | 60 |
| Armored Skeleton | 40 | 10 | 50 |
| Greatsword Skeleton | 35 | 25 | 40 |
| Armored Orc | 60 | 12 | 45 |
| Werewolf | 35 | 12 | 70 |
| Orc Rider | 70 | 15 | 80 |
| Elite Orc | 80 | 20 | 50 |
| Werebear | 100 | 18 | 35 |

**Player:** HP 100, Mana 100, Mana Regen 5.0/s
**Statue (defend target):** HP 200

### 5.7 Sound Effects (`pygame/scripts/sfx_manager.py`)

- Configured via `pygame/data/sfx_config.json`
- Supports volume, speed (resampling via numpy), start/end trim, looping
- Categories: spell sounds, monster sounds, UI sounds

### 5.8 Animation System (`pygame/scripts/resource_manager.py`)

- Sprite sheet-based animation with configurable grid layout
- Loaded from `pygame/data/animations_config.json`
- Supports: idle, walk, attack (multiple), hurt, death, cast_spell, block
- Per-entity scale factors

---

## 6. Difficulties and Solutions

### 6.1 MediaPipe Landmark Jitter

**Problem:** MediaPipe hand landmarks fluctuate between frames even when hands are stationary, causing false gesture switches and unstable predictions.

**Solution:** Implemented **One Euro Filter** (adaptive low-pass filter):
- Heavy smoothing when still (min_cutoff = 1.0)
- Low latency when moving fast (beta = 0.007)
- Replaced previous simple EMA smoothing (alpha = 0.3) which had fixed trade-off

### 6.2 Camera/Window Conflict

**Problem:** Running MediaPipe and Pygame in the same process caused OpenCV window conflicts and camera access Race conditions.

**Solution:** Separated into 2 independent processes:
- Process 1: AI Controller (OpenCV + MediaPipe)
- Process 2: Pygame Game
- Communication via UDP socket (JSON payloads)
- `start_all.py` launches both via `subprocess.Popen`

### 6.3 Animation Retriggering

**Problem:** During spell holding phase, the casting animation was retriggering every frame instead of playing continuously.

**Solution:** Added `casting_stage` state flag:
- Set `PLAYER.casting_stage = "casting"` during holding to prevent `Entity.update()` from resetting animation state
- Reset `casting_stage = None` after spell is actually cast

### 6.4 Continuous Special Spell Casting

**Problem:** Special spells (Crystal, Phoenix) could be cast continuously without the kill counter decreasing.

**Solution:**
- Check `is_locked()` BEFORE setting `selected_spell_index` in FOCUS state
- Call `consume_unlock()` immediately after successful cast in gesture handler
- Reset all spell indices (`PLAYER`, `SPELL_MANAGER`, `SPELL_BAR`) after each cast

### 6.5 False Hand Proximity Detection

**Problem:** Bounding boxes of two separate hands were merging when hands were far apart (fixed tolerance too large).

**Solution:** Dynamic distance-based hand proximity check:
- Calculate center and size of each hand's bounding box
- Only merge when distance between centers < average box size x 1.1
- Adapts to hand size (distance from camera)

### 6.6 Socket Crash on Shutdown

**Problem:** `WinError 10038` when main thread closes socket while listener thread is still using it.

**Solution:** Added socket validity checks and proper `OSError/socket.error` exception handling in listener loop. Break out of loop gracefully when `self.running = False`.

### 6.7 Gesture Spam Prevention

**Problem:** Same gesture repeatedly detected causing spell spam.

**Solution:** 3-state hold system:
- `focus`: Instant spell selection (first detection)
- `holding`: Animation plays, 1-second hold required
- `cast`: Actual spell execution only on release after sufficient hold time
- Minimum 0.5s cooldown between same spell

---

## 7. Improvements and Optimizations

### 7.1 One Euro Filter (Jitter Reduction)

- Replaced simple Exponential Moving Average with adaptive One Euro Filter
- Automatically adjusts smoothing based on movement speed
- 42 independent filter instances per hand for fine-grained control

### 7.2 Dual-Hand Requirement

- Gesture detection only activates when BOTH hands are detected AND close together
- Bounding box visualization: separate boxes (green/red) when apart, merged cyan box when together
- Prevents accidental one-hand detections

### 7.3 Dynamic Wave System

- Wave definitions loaded from `level_config.json`
- Adding/removing waves in config automatically scales the game
- Progressive difficulty: faster spawn delays, stronger monsters in later waves

### 7.4 Victory Screen

- Detects when all waves are cleared AND all monsters are dead
- Shows "VICTORY" with gold text
- 5-second countdown before showing restart prompt
- Player can restart by performing any gesture for 1 second

### 7.5 Kill-Gated Special Spells

- Crystal and Phoenix require 10 kills to unlock
- Shared kill counter across special spells
- Kill counter consumed on cast, preventing repeated free casting
- Visual lock indicator on spell bar

---

## 8. Game Operation Guide

### 8.1 Requirements

```
pip install -r requirements.txt
```

Key dependencies: opencv-python, mediapipe, scikit-learn, pygame, numpy, joblib

### 8.2 Starting the Game

```bash
cd SpellMaster
python start_all.py
```

This launches:
1. **Gesture Server** (OpenCV window with hand detection visualization)
2. **Pygame Game** (game window)

### 8.3 Optional Flags

```bash
python start_all.py --server-only   # Only gesture server (testing)
python start_all.py --game-only     # Only game (keyboard control)
```

### 8.4 Gameplay Flow

1. **Start Screen**: Perform any spell gesture for 1 second to begin
2. **Wave Combat**: Monsters spawn from 3 portals, walk toward the statue
3. **Cast Spells**:
   - Place both hands in front of camera, close together
   - Perform a gesture (hand sign for fire, ice, etc.)
   - Hold for 1 second to charge
   - Release to cast the spell at the nearest monster
4. **Special Spells**: Crystal and Phoenix unlock after 10 kills
5. **Victory**: Clear all 7 waves to win
6. **Game Over**: Statue or player HP reaches 0
7. **Restart**: Perform any gesture for 1 second

### 8.5 Gesture Detection Requirements

- Both hands must be visible to the camera
- Hands must be close together (bounding boxes nearly touching)
- Hold gesture steady for at least 1 second
- Camera resolution: 1280x720

### 8.6 Data Collection (for retraining)

```bash
cd ai_controller/data
python data_collector.py
```

Follow on-screen prompts to record gesture samples.

### 8.7 Model Training

```bash
cd ai_controller/data
python gesture_data_merger.py    # Merge CSVs into final_train.csv
python gesture_model_battle.py   # Train + compare 4 models, save best
```

Output: `ai_controller/data/models/best_spell_model.pkl`

### 8.8 Config Files

| File | Purpose | Edit for |
|------|---------|----------|
| `pygame/data/stat_config.json` | Spell damage, monster stats, player stats | Balance tuning |
| `pygame/data/level_config.json` | Wave definitions, portal positions | Level design |
| `pygame/data/animations_config.json` | Sprite sheet layout | Adding new animations |
| `pygame/data/sfx_config.json` | Sound effect settings | Audio tuning |
