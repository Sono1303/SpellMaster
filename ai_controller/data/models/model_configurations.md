# Model Configuration and Parameters

**Generated:** March 12, 2026

## Performance Comparison Analysis

### Results Summary

```
MODEL                    ACCURACY    F1-SCORE    INFERENCE (ms)
Random Forest            99.96%      0.9996      17.718
SVM (RBF)                99.93%      0.9993      0.831
K-Nearest Neighbors      99.93%      0.9993      5.730
MLP Neural Network       99.96%      0.9996      0.925
```

### Key Observations

**Why Random Forest is "Best" Despite Same Accuracy as MLP?**

- Random Forest and MLP Neural Network both achieve **99.96% accuracy**
- Selection logic: Best model chosen by **highest accuracy**
- When tied on accuracy, the first trained model (Random Forest) is returned
- **Trade-off consideration:** MLP is **19x faster** (0.925 ms vs 17.718 ms)
- For real-time applications: **MLP Neural Network is recommended** despite both having equal accuracy

---

## Model Configurations

### 1. Random Forest Classifier

**Purpose:** Ensemble learning method combining multiple decision trees

**Parameters Used:**

```python
RandomForestClassifier(
    n_estimators=100,           # Number of decision trees in ensemble
    random_state=42,            # Seed for reproducibility
    n_jobs=-1                   # Use all CPU cores for parallel processing
)
```

**Key Characteristics:**

- Trains 100 independent decision trees
- Aggregates predictions via majority voting
- Parallel processing enabled for training efficiency
- Good for feature importance analysis
- Tends to overfit on large feature sets

**Performance:**

- Accuracy: 99.96%
- Inference Time: 17.718 ms (SLOWEST)
- F1-Score: 0.9996

**Use Case:** Batch processing, non-real-time applications where accuracy matters most

---

### 2. Support Vector Machine (SVM) with RBF Kernel

**Purpose:** Finds optimal hyperplane for classification in high-dimensional space

**Parameters Used:**

```python
SVC(
    kernel='rbf',               # Radial Basis Function kernel
    probability=True,           # Enable probability estimates
    random_state=42             # Seed for reproducibility
)
```

**Key Characteristics:**

- RBF kernel handles non-linear decision boundaries
- Probability estimation enabled for confidence scores
- Memory efficient for inference
- Works well with normalized feature inputs
- Excellent for high-dimensional data

**Performance:**

- Accuracy: 99.93%
- Inference Time: 0.831 ms ⭐ **(FASTEST)**
- F1-Score: 0.9993
- Inference Speed Improvement: **21.3x faster than Random Forest**

**Use Case:** ✅ **RECOMMENDED for real-time spell gesture recognition**

---

### 3. K-Nearest Neighbors (KNN)

**Purpose:** Instance-based learning using distance metrics

**Parameters Used:**

```python
KNeighborsClassifier(
    n_neighbors=5               # Use 5 nearest neighbors for voting
)
```

**Key Characteristics:**

- No training phase (lazy learner)
- Prediction requires computing distances to all training samples
- k=5 provides balanced decision boundary smoothing
- Memory intensive (stores all training data)
- Sensitive to feature scaling

**Performance:**

- Accuracy: 99.93%
- Inference Time: 5.730 ms (Middle ground)
- F1-Score: 0.9993

**Use Case:** Moderate-latency applications, good baseline model

---

### 4. Multi-Layer Perceptron (MLP) Neural Network

**Purpose:** Deep learning model with non-linear activation functions

**Parameters Used:**

```python
MLPClassifier(
    hidden_layer_sizes=(64, 32),    # Two hidden layers: 64 → 32 neurons
    max_iter=500,                   # Maximum iterations during training
    random_state=42,                # Seed for reproducibility
    early_stopping=True,            # Stop if validation score stops improving
    validation_fraction=0.1          # Use 10% of training for validation
)
```

**Network Architecture:**

```
Input Layer (features)
    ↓
Hidden Layer 1 (64 neurons, activation=ReLU)
    ↓
Hidden Layer 2 (32 neurons, activation=ReLU)
    ↓
Output Layer (gesture classes, activation=softmax)
```

**Key Characteristics:**

- Early stopping prevents overfitting
- 10% validation split for regularization
- Efficient forward-pass during inference
- Good generalization with proper regularization
- Fastest inference among trained models

**Performance:**

- Accuracy: 99.96% (Tied with Random Forest)
- Inference Time: 0.925 ms ⭐ **(2nd FASTEST)**
- F1-Score: 0.9996

**Use Case:** ✅ **BEST FOR REAL-TIME applications** (equal accuracy, 19x faster than Random Forest)

---

## Detailed Parameter Explanations

### Accuracy Tie - Why MLP = Random Forest?

Both models achieve **99.96% accuracy** but with different characteristics:

| Aspect                | Random Forest      | MLP             |
| --------------------- | ------------------ | --------------- |
| **Accuracy**          | 99.96%             | 99.96%          |
| **Inference Speed**   | 17.7 ms            | 0.9 ms          |
| **Speed Gain**        | —                  | 19.1x faster    |
| **Memory Usage**      | ~100 MB (large)    | ~1-2 MB (small) |
| **Interpretability**  | Feature importance | Black box       |
| **Real-time Capable** | ❌ No              | ✅ Yes          |

### Recommendation for SpellMaster

**For gesture recognition in games, use MLP Neural Network:**

1. ✅ Equal accuracy (99.96%)
2. ✅ 19x faster inference (0.925 ms vs 17.718 ms)
3. ✅ Lower memory footprint
4. ✅ Better for real-time spell casting detection
5. ✅ Can handle multiple predictions per frame without lag

---

## Training Configuration

```python
# Data Split
test_size = 0.2                 # 80% training, 20% testing
random_state = 42              # Fixed seed for reproducibility

# Stratified Split
stratify = True                 # Maintains class distribution in train/test
```

**Label Distribution (Training Set):**

- All gesture classes are balanced
- Stratified split ensures representative distribution
- Prevents bias toward overrepresented classes

---

## Performance Ranking

### By Accuracy

1. 🥇 Random Forest: 99.96%
1. 🥇 MLP Neural Network: 99.96%
1. 🥈 SVM (RBF): 99.93%
1. 🥈 K-Nearest Neighbors: 99.93%

### By Speed (Lower is Better)

1. 🏃 **SVM (RBF): 0.831 ms**
2. 🏃 **MLP Neural Network: 0.925 ms**
3. KNN: 5.730 ms
4. Random Forest: 17.718 ms

### Overall Best for SpellMaster

**MLP Neural Network** - Combines maximum accuracy with excellent inference speed

---

## Conclusion

For the **SpellMaster gesture recognition system**, the **MLP Neural Network** is the optimal choice despite Random Forest being algorithmically "best" by accuracy. The 19x speed improvement will provide a smoother, more responsive spell-casting experience without sacrificing recognition accuracy.
