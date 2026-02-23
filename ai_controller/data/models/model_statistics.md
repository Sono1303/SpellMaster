# Gesture Spell Model Comparison Report

**Generated:** 2026-02-23 00:06:12

## Model Performance Summary

**Best Model:** Random Forest

**Accuracy:** 75.00%

**F1-Score (Weighted):** 0.6667

**Inference Time:** 16.336 ms

## Detailed Model Comparison

| Model | Accuracy (%) | F1-Score | Inference Time (ms) |
|-------|--------------|----------|---------------------|
| Random Forest (WINNER) | 75.00% | 0.6667 | 16.336 |
| SVM (RBF) | 75.00% | 0.6667 | 0.755 |
| K-Nearest Neighbors | 75.00% | 0.6667 | 1.443 |

## Rankings

**Highest Accuracy:** Random Forest (75.00%)

**Fastest Inference:** SVM (RBF) (0.755 ms)

## Training Data Statistics

**Total Samples:** 3998

**Training Set:** 3198 samples (79%)

**Test Set:** 800 samples (20%)

**Number of Features:** 84

### Label Distribution (Training Set)

- Tiger: 800 samples (25.0%)
- Dragon: 800 samples (25.0%)
- Rat: 800 samples (25.0%)
- Ox: 798 samples (25.0%)

## Detailed Classification Report (Best Model)

```
              precision    recall  f1-score   support

      Dragon       0.50      1.00      0.67       200
          Ox       1.00      1.00      1.00       200
         Rat       1.00      1.00      1.00       200
       Tiger       0.00      0.00      0.00       200

    accuracy                           0.75       800
   macro avg       0.62      0.75      0.67       800
weighted avg       0.62      0.75      0.67       800
```

## Model Descriptions

**Random Forest:** Ensemble method with 100 decision trees. Good for overall accuracy and feature importance.

**SVM (RBF):** Support Vector Machine with Radial Basis Function kernel. Powerful for non-linear classification with balanced performance.

**K-Nearest Neighbors:** Instance-based learning algorithm (k=5). Simple but can be slow for inference.

**MLP Neural Network:** Multi-layer perceptron with hidden layers (64, 32). Often fastest inference time, good for real-time applications.

