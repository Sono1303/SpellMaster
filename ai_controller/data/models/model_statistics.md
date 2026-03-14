# Gesture Spell Model Comparison Report

**Generated:** 2026-03-12 22:08:09

## Model Performance Summary

**Best Model (Balanced Score):** MLP Neural Network

**Accuracy:** 99.96%

**F1-Score (Weighted):** 0.9996

**Inference Time:** 1.163 ms

**Balanced Score:** 0.9997

### Selection Logic

The best model is selected using a **balanced scoring system** that considers both:
- **Accuracy (70% weight):** Model precision for gesture recognition
- **Speed (30% weight):** Response time for real-time spell casting

This weighted approach optimizes for SpellMaster use case where both accuracy and real-time responsiveness are crucial.

## Detailed Model Comparison

| Model | Accuracy (%) | F1-Score | Inference Time (ms) |
|-------|--------------|----------|---------------------|
| Random Forest | 99.96% | 0.9996 | 26.610 |
| MLP Neural Network (WINNER) | 99.96% | 0.9996 | 1.163 |
| SVM (RBF) | 99.93% | 0.9993 | 1.071 |
| K-Nearest Neighbors | 99.93% | 0.9993 | 12.359 |

## Rankings

**Highest Accuracy:** Random Forest (99.96%)

**Fastest Inference:** SVM (RBF) (1.071 ms)

## Training Data Statistics

**Total Samples:** 22753

**Training Set:** 18202 samples (79%)

**Test Set:** 4551 samples (20%)

**Number of Features:** 84

### Label Distribution (Training Set)

- Ice: 3040 samples (16.7%)
- Fire: 2879 samples (15.8%)
- Dark: 2720 samples (14.9%)
- Lightning: 2400 samples (13.2%)
- Air: 2400 samples (13.2%)
- Earth: 2400 samples (13.2%)
- Water: 2363 samples (13.0%)

## Detailed Classification Report (Best Model)

```
              precision    recall  f1-score   support

         Air       1.00      1.00      1.00       600
        Dark       1.00      1.00      1.00       680
       Earth       1.00      1.00      1.00       600
        Fire       1.00      1.00      1.00       720
         Ice       1.00      1.00      1.00       760
   Lightning       1.00      1.00      1.00       600
       Water       1.00      1.00      1.00       591

    accuracy                           1.00      4551
   macro avg       1.00      1.00      1.00      4551
weighted avg       1.00      1.00      1.00      4551
```

## Model Descriptions

**Random Forest:** Ensemble method with 100 decision trees. Good for overall accuracy and feature importance.

**SVM (RBF):** Support Vector Machine with Radial Basis Function kernel. Powerful for non-linear classification with balanced performance.

**K-Nearest Neighbors:** Instance-based learning algorithm (k=5). Simple but can be slow for inference.

**MLP Neural Network:** Multi-layer perceptron with hidden layers (64, 32). Often fastest inference time, good for real-time applications.

