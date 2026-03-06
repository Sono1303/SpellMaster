# Gesture Spell Model Comparison Report

**Generated:** 2026-03-07 00:05:00

## Model Performance Summary

**Best Model:** SVM (RBF)

**Accuracy:** 100.00%

**F1-Score (Weighted):** 1.0000

**Inference Time:** 0.860 ms

## Detailed Model Comparison

| Model | Accuracy (%) | F1-Score | Inference Time (ms) |
|-------|--------------|----------|---------------------|
| SVM (RBF) (WINNER) | 100.00% | 1.0000 | 0.860 |
| Random Forest | 99.81% | 0.9981 | 18.441 |
| K-Nearest Neighbors | 99.81% | 0.9981 | 4.560 |
| MLP Neural Network | 99.62% | 0.9962 | 0.890 |

## Rankings

**Highest Accuracy:** SVM (RBF) (100.00%)

**Fastest Inference:** SVM (RBF) (0.860 ms)

## Training Data Statistics

**Total Samples:** 8000

**Training Set:** 6400 samples (80%)

**Test Set:** 1600 samples (20%)

**Number of Features:** 84

### Label Distribution (Training Set)

- Fire: 1600 samples (25.0%)
- Earth: 1600 samples (25.0%)
- Water: 1600 samples (25.0%)
- Air: 1600 samples (25.0%)

## Detailed Classification Report (Best Model)

```
              precision    recall  f1-score   support

         Air       1.00      1.00      1.00       400
       Earth       1.00      1.00      1.00       400
        Fire       1.00      1.00      1.00       400
       Water       1.00      1.00      1.00       400

    accuracy                           1.00      1600
   macro avg       1.00      1.00      1.00      1600
weighted avg       1.00      1.00      1.00      1600
```

## Model Descriptions

**Random Forest:** Ensemble method with 100 decision trees. Good for overall accuracy and feature importance.

**SVM (RBF):** Support Vector Machine with Radial Basis Function kernel. Powerful for non-linear classification with balanced performance.

**K-Nearest Neighbors:** Instance-based learning algorithm (k=5). Simple but can be slow for inference.

**MLP Neural Network:** Multi-layer perceptron with hidden layers (64, 32). Often fastest inference time, good for real-time applications.

