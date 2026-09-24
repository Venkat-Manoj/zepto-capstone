# Module 2 — Analytics Pipeline

Run `01_eda.py` first, then `02_modeling.py`. The raw Titanic dataset is loaded through Seaborn only when the committed `titanic.csv` fallback is absent; the modeling stage reads that same CSV and never calls `sns.load_dataset` again.

Outputs include the EDA report, missingness/cleaning decisions, required plots, model metrics, confusion matrices, ROC curves, imbalance comparison, Random Forest GridSearch/OOB results, fare regression metrics/residual plot, and the complete `joblib` pipeline.
