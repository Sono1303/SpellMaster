# Gesture Spell Model Comparison Report

**Generated:** 2026-03-30 20:58:17

## Model Performance Summary

**Best Model (Balanced Score):** SVM (RBF)

**Accuracy:** 100.00%

**F1-Score (Weighted):** 1.0000

**Inference Time:** 0.915 ms

**Balanced Score:** 1.0000

### Selection Logic

The best model is selected using a **balanced scoring system** that considers both:
- **Accuracy (70% weight):** Model precision for gesture recognition
- **Speed (30% weight):** Response time for real-time spell casting

This weighted approach optimizes for SpellMaster use case where both accuracy and real-time responsiveness are crucial.

## Detailed Model Comparison

| Model | Accuracy (%) | F1-Score | Inference Time (ms) |
|-------|--------------|----------|---------------------|
| SVM (RBF) (WINNER) | 100.00% | 1.0000 | 0.915 |
| Random Forest | 99.98% | 0.9998 | 17.231 |
| K-Nearest Neighbors | 99.97% | 0.9997 | 2.846 |

## Rankings

**Highest Accuracy:** SVM (RBF) (100.00%)

**Fastest Inference:** SVM (RBF) (0.915 ms)

## Training Data Statistics

**Total Samples:** 31740

**Training Set:** 25392 samples (80%)

**Test Set:** 6348 samples (20%)

**Number of Features:** 84

### Label Distribution (Training Set)

- Ice: 3040 samples (12.0%)
- Fire: 2879 samples (11.3%)
- Dark: 2720 samples (10.7%)
- Earth: 2400 samples (9.5%)
- Crystal: 2400 samples (9.5%)
- Phoenix: 2400 samples (9.5%)
- Lightning: 2400 samples (9.5%)
- Air: 2400 samples (9.5%)
- Light: 2390 samples (9.4%)
- Water: 2363 samples (9.3%)

## Detailed Classification Report (Best Model)

```
              precision    recall  f1-score   support

         Air       1.00      1.00      1.00       600
     Crystal       1.00      1.00      1.00       600
        Dark       1.00      1.00      1.00       680
       Earth       1.00      1.00      1.00       600
        Fire       1.00      1.00      1.00       720
         Ice       1.00      1.00      1.00       760
       Light       1.00      1.00      1.00       597
   Lightning       1.00      1.00      1.00       600
     Phoenix       1.00      1.00      1.00       600
       Water       1.00      1.00      1.00       591

    accuracy                           1.00      6348
   macro avg       1.00      1.00      1.00      6348
weighted avg       1.00      1.00      1.00      6348
```

## Model Descriptions

**Random Forest:** Ensemble method with 100 decision trees. Good for overall accuracy and feature importance.

**SVM (RBF):** Support Vector Machine with Radial Basis Function kernel. Powerful for non-linear classification with balanced performance.

**K-Nearest Neighbors:** Instance-based learning algorithm (k=5). Simple but can be slow for inference.

**MLP Neural Network:** Multi-layer perceptron with hidden layers (64, 32). Often fastest inference time, good for real-time applications.

