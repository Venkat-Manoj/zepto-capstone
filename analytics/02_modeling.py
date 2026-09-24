from __future__ import annotations

from pathlib import Path
import warnings

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, plot_tree

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CSV = ROOT / "titanic.csv"
warnings.filterwarnings("ignore", category=FutureWarning)


CLASSIFICATION_NUMERIC = ["pclass", "age", "sibsp", "parch", "fare"]
CLASSIFICATION_CATEGORICAL = ["sex", "embarked"]
CLASSIFICATION_EXCLUDE = {
    "survived",
    "alive",
    "class",
    "who",
    "adult_male",
    "alone",
    "deck",
    "embark_town",
}


def make_classifier_preprocessor(num_cols: list[str], cat_cols: list[str]) -> ColumnTransformer:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("num", numeric, num_cols),
            ("cat", categorical, cat_cols),
        ]
    )


def evaluate_classifier(name: str, model, X_test: pd.DataFrame, y_test: pd.Series):
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else model.decision_function(X_test)
    metrics = {
        "model": name,
        "accuracy": accuracy_score(y_test, pred),
        "precision": precision_score(y_test, pred, zero_division=0),
        "recall": recall_score(y_test, pred, zero_division=0),
        "f1": f1_score(y_test, pred, zero_division=0),
        "auc": roc_auc_score(y_test, proba),
    }
    return metrics, pred, proba


def main() -> None:
    # Modeling reads only the one committed fallback created by 01_eda.py.
    df = pd.read_csv(CSV)
    if "survived" not in df.columns:
        raise ValueError("titanic.csv must contain the survived target column.")

    target = "survived"
    feature_cols = [c for c in df.columns if c not in CLASSIFICATION_EXCLUDE]
    X = df[feature_cols].copy()
    y = df[target].astype(int)
    numeric_cols = [c for c in CLASSIFICATION_NUMERIC if c in X.columns]
    cat_cols = [c for c in CLASSIFICATION_CATEGORICAL if c in X.columns]

    # Required: split first, before any fitting of imputation/encoding/scaling.
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    class_balance = (
        y.value_counts(normalize=True)
        .rename(index={0: "not_survived", 1: "survived"})
        .mul(100)
        .rename("percentage")
    )
    train_balance = y_train.value_counts(normalize=True).rename(index={0: "not_survived", 1: "survived"}).mul(100).rename("percentage")
    test_balance = y_test.value_counts(normalize=True).rename(index={0: "not_survived", 1: "survived"}).mul(100).rename("percentage")

    lines = [
        "# Modeling Report",
        "",
        "## Stratified split and class balance",
        "",
        "### Overall class balance",
        class_balance.round(2).to_frame().to_markdown(),
        "",
        "### Training class balance",
        train_balance.round(2).to_frame().to_markdown(),
        "",
        "### Test class balance",
        test_balance.round(2).to_frame().to_markdown(),
        "",
        "Stratification matters because the target contains two outcome classes with an observed imbalance. Splitting with `stratify=y` preserves approximately the same not-survived/survived proportion in train and test, making model evaluation less sensitive to an accidental class-distribution shift.",
    ]

    pre = make_classifier_preprocessor(numeric_cols, cat_cols)
    models = {
        "Logistic Regression": Pipeline(
            [("preprocess", pre), ("model", LogisticRegression(max_iter=2000, random_state=42))]
        ),
        "Decision Tree": Pipeline(
            [("preprocess", make_classifier_preprocessor(numeric_cols, cat_cols)), ("model", DecisionTreeClassifier(max_depth=5, random_state=42))]
        ),
        "Random Forest": Pipeline(
            [("preprocess", make_classifier_preprocessor(numeric_cols, cat_cols)), ("model", RandomForestClassifier(n_estimators=300, random_state=42))]
        ),
    }

    results: list[dict] = []
    roc_data = []
    for name, model in models.items():
        model.fit(X_train, y_train)
        metrics, pred, proba = evaluate_classifier(name, model, X_test, y_test)
        results.append(metrics)
        roc_data.append((name, y_test, proba))

        cm = confusion_matrix(y_test, pred)
        pd.DataFrame(
            cm,
            index=["actual_not_survived", "actual_survived"],
            columns=["pred_not_survived", "pred_survived"],
        ).to_csv(OUT / f"confusion_{name.lower().replace(' ', '_')}.csv")

        if name == "Decision Tree":
            feature_names = model.named_steps["preprocess"].get_feature_names_out()
            fig, ax = plt.subplots(figsize=(18, 9))
            plot_tree(
                model.named_steps["model"],
                feature_names=feature_names,
                class_names=["Not survived", "Survived"],
                filled=False,
                max_depth=5,
                ax=ax,
            )
            ax.set_title("Decision Tree")
            plt.tight_layout()
            plt.savefig(OUT / "decision_tree.png", dpi=160, bbox_inches="tight")
            plt.close()

    metrics_df = pd.DataFrame(results)
    lines += ["", "## Classifier comparison", "", metrics_df.round(4).to_markdown(index=False)]

    fig, ax = plt.subplots(figsize=(8, 6))
    for name, yt, proba in roc_data:
        fpr, tpr, _ = roc_curve(yt, proba)
        auc = roc_auc_score(yt, proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], linestyle="--")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curves")
    ax.legend()
    plt.tight_layout()
    plt.savefig(OUT / "roc_curves.png", dpi=160, bbox_inches="tight")
    plt.close()

    # Imbalance comparison: same model family and same untouched test set for every variant.
    variants = {}
    for label, estimator in [
        ("baseline", RandomForestClassifier(n_estimators=300, random_state=42)),
        ("class_weight_balanced", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42)),
    ]:
        pipe = Pipeline(
            [
                ("preprocess", make_classifier_preprocessor(numeric_cols, cat_cols)),
                ("model", estimator),
            ]
        )
        pipe.fit(X_train, y_train)
        m, _, _ = evaluate_classifier(label, pipe, X_test, y_test)
        variants[label] = m

    smote_pipe = ImbPipeline(
        [
            ("preprocess", make_classifier_preprocessor(numeric_cols, cat_cols)),
            ("smote", SMOTE(random_state=42)),
            ("model", RandomForestClassifier(n_estimators=300, random_state=42)),
        ]
    )
    smote_pipe.fit(X_train, y_train)
    m, _, _ = evaluate_classifier("smote", smote_pipe, X_test, y_test)
    variants["smote"] = m

    imbalance_df = (
        pd.DataFrame([variants[k] for k in ["baseline", "class_weight_balanced", "smote"]])
        [["model", "precision", "recall", "f1"]]
    )
    imbalance_best = imbalance_df.sort_values(["f1", "recall", "precision"], ascending=False).iloc[0]
    lines += [
        "",
        "## Imbalance handling comparison",
        "",
        imbalance_df.round(4).to_markdown(index=False),
        "",
        "The baseline, `class_weight='balanced'`, and SMOTE variants use the same original train/test split and the same untouched test set. SMOTE is inside an imbalanced-learn pipeline, so synthetic samples are created only from the training data after the split.",
        "",
        f"In this run, **{imbalance_best['model']}** gave the highest F1 (**{imbalance_best['f1']:.4f}**) with precision **{imbalance_best['precision']:.4f}** and recall **{imbalance_best['recall']:.4f}**, so it had the strongest observed balance of positive-class precision and recall among the three variants. This comparison is empirical on the held-out test set; the operational choice should also consider whether false negatives or false positives are more costly.",
    ]

    # GridSearchCV for Random Forest; oob_score=True is enabled on the estimator.
    rf_pipe = Pipeline(
        [
            ("preprocess", make_classifier_preprocessor(numeric_cols, cat_cols)),
            ("model", RandomForestClassifier(oob_score=True, random_state=42, n_jobs=-1)),
        ]
    )
    grid = GridSearchCV(
        rf_pipe,
        param_grid={
            "model__n_estimators": [200, 300],
            "model__max_depth": [None, 5, 10],
            "model__max_features": ["sqrt", "log2"],
        },
        scoring="f1",
        cv=5,
        n_jobs=-1,
        refit=True,
    )
    grid.fit(X_train, y_train)
    best_rf = grid.best_estimator_
    best_oob = best_rf.named_steps["model"].oob_score_
    lines += [
        "",
        "## Random Forest GridSearchCV",
        "",
        f"Best parameters: `{grid.best_params_}`",
        "",
        f"Best cross-validation F1: **{grid.best_score_:.4f}**",
        "",
        f"Best estimator OOB score: **{best_oob:.4f}**",
    ]

    # Regression side-task: use all other available cleaned features except the fare target itself.
    reg_features = [c for c in df.columns if c != "fare"]
    Xr = df[reg_features].copy()
    yr = df["fare"].copy()
    Xr_train, Xr_test, yr_train, yr_test = train_test_split(
        Xr, yr, test_size=0.2, random_state=42
    )
    r_num = Xr_train.select_dtypes(include=np.number).columns.tolist()
    r_cat = [c for c in Xr.columns if c not in r_num]
    reg_pre = ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                r_num,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                r_cat,
            ),
        ]
    )
    reg_pipe = Pipeline([("preprocess", reg_pre), ("model", LinearRegression())])
    reg_pipe.fit(Xr_train, yr_train)
    pred_fare = reg_pipe.predict(Xr_test)
    mae = mean_absolute_error(yr_test, pred_fare)
    rmse = mean_squared_error(yr_test, pred_fare) ** 0.5
    r2 = r2_score(yr_test, pred_fare)
    transformed_test = reg_pipe.named_steps["preprocess"].transform(Xr_test)
    n, p = len(yr_test), transformed_test.shape[1]
    if n - p - 1 <= 0:
        raise ValueError("Adjusted R² is undefined because the transformed test set has too many predictors.")
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)

    residuals = yr_test - pred_fare
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.scatterplot(x=pred_fare, y=residuals, ax=ax)
    ax.axhline(0, linestyle="--")
    ax.set_xlabel("Predicted fare")
    ax.set_ylabel("Residual")
    ax.set_title("Fare regression residual plot")
    plt.tight_layout()
    plt.savefig(OUT / "fare_residuals.png", dpi=160, bbox_inches="tight")
    plt.close()

    corr_resid_fitted = float(np.corrcoef(pred_fare, np.abs(residuals))[0, 1])
    hetero = (
        "evidence of heteroscedasticity"
        if abs(corr_resid_fitted) >= 0.25
        else "no strong evidence of heteroscedasticity"
    )
    reg_df = pd.DataFrame(
        [
            {
                "model": "Linear Regression (fare)",
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "Adjusted_R2": adj_r2,
            }
        ]
    )
    lines += [
        "",
        "## Regression side-task",
        "",
        reg_df.round(4).to_markdown(index=False),
        "",
        f"The residual plot is saved as `outputs/fare_residuals.png`. The correlation between fitted values and absolute residuals is **{corr_resid_fitted:.4f}**, so this run shows **{hetero}** under the diagnostic rule used here; the conclusion should also be checked visually against the residual plot for a funnel or other systematic spread.",
    ]

    # Separate metric groups: classifier scores and regression errors are different metric families.
    final_comparison = pd.DataFrame(
        [
            {
                "model_type": "classification",
                "model": row["model"],
                "accuracy": row["accuracy"],
                "precision": row["precision"],
                "recall": row["recall"],
                "f1": row["f1"],
                "auc": row["auc"],
                "MAE": np.nan,
                "RMSE": np.nan,
                "R2": np.nan,
                "Adjusted_R2": np.nan,
            }
            for row in results
        ]
        + [
            {
                "model_type": "regression",
                "model": reg_df.loc[0, "model"],
                "accuracy": np.nan,
                "precision": np.nan,
                "recall": np.nan,
                "f1": np.nan,
                "auc": np.nan,
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "Adjusted_R2": adj_r2,
            }
        ]
    )
    lines += [
        "",
        "## Final model comparison",
        "",
        final_comparison.round(4).to_markdown(index=False),
        "",
        "Classification metrics (`accuracy`, `precision`, `recall`, `F1`, `AUC`) and regression metrics (`MAE`, `RMSE`, `R²`, `Adjusted R²`) are shown as separate metric groups and are not directly comparable as a single numerical scale.",
        "",
        "### Deployment recommendation",
        "",
    ]

    deploy_row = metrics_df.sort_values(["f1", "auc"], ascending=False).iloc[0]
    lines.append(
        f"Based on the held-out test results from this run, **{deploy_row['model']}** is the classifier selected for deployment because it has the highest F1 score ({deploy_row['f1']:.4f}) and an AUC of {deploy_row['auc']:.4f}. "
        f"Its accuracy is {deploy_row['accuracy']:.4f}, precision is {deploy_row['precision']:.4f}, and recall is {deploy_row['recall']:.4f}. "
        "This choice emphasizes balanced positive-class performance while still considering ranking quality through AUC. "
        "The fare-regression metrics remain a separate model-type group and are not used to choose the classifier."
    )

    # Save the complete preprocessing + estimator pipeline, not the bare model.
    final_pipeline = grid.best_estimator_
    pipeline_path = OUT / "best_classifier_pipeline.joblib"
    joblib.dump(final_pipeline, pipeline_path)
    reloaded = joblib.load(pipeline_path)
    reload_pred = reloaded.predict(X_test.iloc[:5])
    lines += [
        "",
        "## Saved artifact verification",
        "",
        f"Saved complete pipeline: `{pipeline_path.relative_to(ROOT.parent)}`",
        "",
        f"Reloaded pipeline accepted raw test rows and predicted: `{reload_pred.tolist()}`",
    ]

    metrics_df.to_csv(OUT / "classifier_metrics.csv", index=False)
    imbalance_df.to_csv(OUT / "imbalance_comparison.csv", index=False)
    reg_df.to_csv(OUT / "regression_metrics.csv", index=False)
    final_comparison.to_csv(OUT / "final_model_comparison.csv", index=False)
    (OUT / "modeling_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("Modeling complete:", OUT / "modeling_report.md")


if __name__ == "__main__":
    main()
