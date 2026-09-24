# Modeling Report

## Stratified split and class balance

### Overall class balance
| survived     |   percentage |
|:-------------|-------------:|
| not_survived |        61.62 |
| survived     |        38.38 |

### Training class balance
| survived     |   percentage |
|:-------------|-------------:|
| not_survived |        61.66 |
| survived     |        38.34 |

### Test class balance
| survived     |   percentage |
|:-------------|-------------:|
| not_survived |        61.45 |
| survived     |        38.55 |

Stratification matters because the target contains two outcome classes with an observed imbalance. Splitting with `stratify=y` preserves approximately the same not-survived/survived proportion in train and test, making model evaluation less sensitive to an accidental class-distribution shift.

## Classifier comparison

| model               |   accuracy |   precision |   recall |     f1 |    auc |
|:--------------------|-----------:|------------:|---------:|-------:|-------:|
| Logistic Regression |     0.8045 |      0.7931 |   0.6667 | 0.7244 | 0.8437 |
| Decision Tree       |     0.7654 |      0.7547 |   0.5797 | 0.6557 | 0.7971 |
| Random Forest       |     0.8101 |      0.7966 |   0.6812 | 0.7344 | 0.8287 |

## Imbalance handling comparison

| model                 |   precision |   recall |     f1 |
|:----------------------|------------:|---------:|-------:|
| baseline              |      0.7966 |   0.6812 | 0.7344 |
| class_weight_balanced |      0.8    |   0.6957 | 0.7442 |
| smote                 |      0.7727 |   0.7391 | 0.7556 |

The baseline, `class_weight='balanced'`, and SMOTE variants use the same original train/test split and the same untouched test set. SMOTE is inside an imbalanced-learn pipeline, so synthetic samples are created only from the training data after the split.

In this run, **smote** gave the highest F1 (**0.7556**) with precision **0.7727** and recall **0.7391**, so it had the strongest observed balance of positive-class precision and recall among the three variants. This comparison is empirical on the held-out test set; the operational choice should also consider whether false negatives or false positives are more costly.

## Random Forest GridSearchCV

Best parameters: `{'model__max_depth': 5, 'model__max_features': 'sqrt', 'model__n_estimators': 200}`

Best cross-validation F1: **0.7436**

Best estimator OOB score: **0.8301**

## Regression side-task

| model                    |     MAE |    RMSE |     R2 |   Adjusted_R2 |
|:-------------------------|--------:|--------:|-------:|--------------:|
| Linear Regression (fare) | 17.5456 | 29.3941 | 0.4416 |        0.3098 |

The residual plot is saved as `outputs/fare_residuals.png`. The correlation between fitted values and absolute residuals is **0.6506**, so this run shows **evidence of heteroscedasticity** under the diagnostic rule used here; the conclusion should also be checked visually against the residual plot for a funnel or other systematic spread.

## Final model comparison

| model_type     | model                    |   accuracy |   precision |   recall |       f1 |      auc |      MAE |     RMSE |       R2 |   Adjusted_R2 |
|:---------------|:-------------------------|-----------:|------------:|---------:|---------:|---------:|---------:|---------:|---------:|--------------:|
| classification | Logistic Regression      |     0.8045 |      0.7931 |   0.6667 |   0.7244 |   0.8437 | nan      | nan      | nan      |      nan      |
| classification | Decision Tree            |     0.7654 |      0.7547 |   0.5797 |   0.6557 |   0.7971 | nan      | nan      | nan      |      nan      |
| classification | Random Forest            |     0.8101 |      0.7966 |   0.6812 |   0.7344 |   0.8287 | nan      | nan      | nan      |      nan      |
| regression     | Linear Regression (fare) |   nan      |    nan      | nan      | nan      | nan      |  17.5456 |  29.3941 |   0.4416 |        0.3098 |

Classification metrics (`accuracy`, `precision`, `recall`, `F1`, `AUC`) and regression metrics (`MAE`, `RMSE`, `R²`, `Adjusted R²`) are shown as separate metric groups and are not directly comparable as a single numerical scale.

### Deployment recommendation

Based on the held-out test results from this run, **Random Forest** is the classifier selected for deployment because it has the highest F1 score (0.7344) and an AUC of 0.8287. Its accuracy is 0.8101, precision is 0.7966, and recall is 0.6812. This choice emphasizes balanced positive-class performance while still considering ranking quality through AUC. The fare-regression metrics remain a separate model-type group and are not used to choose the classifier.

## Saved artifact verification

Saved complete pipeline: `analytics/outputs/best_classifier_pipeline.joblib`

Reloaded pipeline accepted raw test rows and predicted: `[0, 0, 0, 0, 1]`