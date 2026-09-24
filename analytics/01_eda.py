from __future__ import annotations

from pathlib import Path
import pandas as pd
import numpy as np
from io import StringIO
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CSV = ROOT / "titanic.csv"


def load_once() -> pd.DataFrame:
    """Load Titanic once via Seaborn, with the committed CSV as an offline fallback."""
    try:
        # This is the module's single call to the required network/cache loader.
        df = sns.load_dataset("titanic")
        df.to_csv(CSV, index=False)
        return df
    except Exception as exc:
        if CSV.exists():
            print(f"Seaborn Titanic load unavailable ({exc!r}); using committed offline fallback: {CSV}")
            return pd.read_csv(CSV)
        raise


def pct_missing(df: pd.DataFrame) -> pd.Series:
    return (df.isna().mean() * 100).loc[lambda s: s > 0].sort_values(ascending=False)


def clean_for_eda(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    decisions = []
    missing = pct_missing(out)
    for col, pct in missing.items():
        if pct < 5:
            before = len(out)
            out = out.dropna(subset=[col])
            decisions.append(f"- `{col}`: {pct:.2f}% missing (<5%), so dropped affected rows ({before - len(out)} rows).")
        elif pct <= 30:
            if pd.api.types.is_numeric_dtype(out[col]):
                value = out[col].median()
            else:
                value = out[col].mode(dropna=True).iloc[0]
            out[col] = out[col].fillna(value)
            decisions.append(f"- `{col}`: {pct:.2f}% missing (5–30%), so imputed with {'median' if pd.api.types.is_numeric_dtype(out[col]) else 'mode'}.")
        else:
            # `deck` has very high missingness in the seaborn Titanic data. Keep it as an explicit missing category.
            if col == "deck" and not pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col].astype("object").where(out[col].notna(), "Missing")
                decisions.append(f"- `{col}`: {pct:.2f}% missing (>30%); retained it with an explicit `Missing` category because dropping the feature would discard a potentially useful cabin-location signal while direct imputation would be misleading.")
            else:
                out = out.drop(columns=[col])
                decisions.append(f"- `{col}`: {pct:.2f}% missing (>30%); dropped the column because direct imputation would be unreliable.")
    return out, decisions


def iqr_count(s: pd.Series) -> tuple[float, float, int]:
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return low, high, int(((s < low) | (s > high)).sum())


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(OUT / name, dpi=160, bbox_inches="tight")
    plt.close()


def main() -> None:
    raw = load_once()
    print("df.shape:", raw.shape)
    raw.info()
    print("df.describe():\n", raw.describe(include="all"))
    # Required immediate fallback save after the single raw load. If the committed file existed,
    # rewriting it preserves the same data and makes the behavior explicit.
    raw.to_csv(CSV, index=False)

    profile = []
    profile.append(f"# EDA Report\n\n## Raw shape\n\n`{raw.shape}`\n")
    info_buf = StringIO()
    raw.info(buf=info_buf)
    profile.append("## `df.info()`\n\n```text\n" + info_buf.getvalue() + "```\n")
    profile.append("## `df.describe()`\n\n" + raw.describe(include="all").to_string())
    profile.append("\n## Missing values\n\n" + pct_missing(raw).to_frame("missing_pct").round(2).to_markdown())

    df, decisions = clean_for_eda(raw)
    profile.append("\n## Cleaning decisions\n\n" + "\n".join(decisions))
    profile.append(f"\nCleaned shape: `{df.shape}`")

    # Histograms + boxplots for age and fare.
    for col in ["age", "fare"]:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(df[col].dropna(), bins=30, alpha=0.8)
        ax.set_title(f"Histogram — {col}")
        savefig(f"{col}_hist.png")
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.boxplot(df[col].dropna(), vert=False)
        ax.set_title(f"Box plot — {col}")
        savefig(f"{col}_box.png")

    age_low, age_high, age_out = iqr_count(df["age"])
    fare_low, fare_high, fare_out = iqr_count(df["fare"])
    fare_mean, fare_median, fare_mode = df["fare"].mean(), df["fare"].median(), df["fare"].mode().iloc[0]
    skew = "right-skewed" if fare_mean > fare_median > fare_mode else "left-skewed" if fare_mean < fare_median < fare_mode else "not strictly monotonic by mean/median/mode"
    profile.append(f"\n## Univariate results\n\n- Age IQR bounds: [{age_low:.3f}, {age_high:.3f}], outliers: **{age_out}**.\n- Fare IQR bounds: [{fare_low:.3f}, {fare_high:.3f}], outliers: **{fare_out}**.\n- Fare mean: **{fare_mean:.4f}**; median: **{fare_median:.4f}**; mode: **{fare_mode:.4f}**.\n- By the mean/median/mode ordering, fare is **{skew}**.")

    # Bivariate survival rates with boolean masks.
    female_mask = df["sex"].eq("female")
    male_mask = df["sex"].eq("male")
    class_masks = {p: df["pclass"].eq(p) for p in sorted(df["pclass"].unique())}
    survival_by_sex = pd.Series({
        "female": df.loc[female_mask, "survived"].mean() * 100,
        "male": df.loc[male_mask, "survived"].mean() * 100,
    })
    survival_by_class = pd.Series({p: df.loc[mask, "survived"].mean() * 100 for p, mask in class_masks.items()})
    sex_class_rows = []
    for sex in ["female", "male"]:
        for p in sorted(df["pclass"].unique()):
            mask = (df["sex"].eq(sex)) & (df["pclass"].eq(p))
            sex_class_rows.append({"sex": sex, "pclass": p, "survival_rate_pct": df.loc[mask, "survived"].mean() * 100})
    sex_class = pd.DataFrame(sex_class_rows)
    profile.append("\n## Survival rates\n\n### By sex\n\n" + survival_by_sex.round(2).to_frame("survival_rate_pct").to_markdown())
    profile.append("\n### By pclass\n\n" + survival_by_class.round(2).to_frame("survival_rate_pct").to_markdown())
    profile.append("\n### By sex and pclass\n\n" + sex_class.round(2).to_markdown(index=False))

    corr_cols = ["survived", "pclass", "age", "sibsp", "parch", "fare"]
    corr = df[corr_cols].corr()
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, ax=ax)
    ax.set_title("Titanic numeric correlation matrix")
    savefig("correlation_heatmap.png")
    pairs = []
    for i in range(len(corr_cols)):
        for j in range(i + 1, len(corr_cols)):
            pairs.append((abs(corr.iloc[i, j]), corr.iloc[i, j], corr_cols[i], corr_cols[j]))
    pairs.sort(reverse=True)
    strongest = pairs[:2]
    profile.append("\n## Exact six-column correlation matrix\n\n" + corr.round(4).to_markdown())
    profile.append("\n### Two strongest absolute off-diagonal correlations\n\n" + "\n".join([f"- `{a}` vs `{b}`: r = {r:.4f} (|r| = {absr:.4f})." for absr, r, a, b in strongest]))

    # Four distinct multivariate charts with written interpretations.
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.barplot(data=df, x="pclass", y="survived", hue="sex", errorbar=None, ax=ax)
    ax.set_ylabel("Survival rate")
    ax.set_title("Survival by class and sex")
    savefig("story_1_survival_class_sex.png")
    profile.append("\n## Chart interpretation 1 — survival by class and sex\n\nWomen have substantially higher survival rates than men in every passenger class in the cleaned data, and first/second-class passengers have higher survival rates than third-class passengers within each sex. The separation by both variables shows that survival is associated with their combination rather than with either feature alone.")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxplot(data=df, x="pclass", y="fare", hue="survived", ax=ax)
    ax.set_title("Fare distributions by class and survival")
    savefig("story_2_fare_class_survival.png")
    profile.append("\n## Chart interpretation 2 — fare, class, and survival\n\nFare is much higher and more dispersed in the upper passenger classes, while survivors generally occupy higher-fare portions of the class-specific distributions. Because fare and class are strongly related, the chart supports an economic-position pattern without treating fare as an independent explanation of survival.")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.scatterplot(data=df, x="age", y="fare", hue="survived", style="sex", alpha=0.65, ax=ax)
    ax.set_title("Age vs fare by survival and sex")
    savefig("story_3_age_fare_survival.png")
    profile.append("\n## Chart interpretation 3 — age, fare, sex, and survival\n\nThe points show substantial overlap, but survival outcomes are not distributed uniformly across age, fare, and sex. Combining the variables in one view reinforces the earlier pattern that demographic and economic factors jointly describe survival better than any single variable alone.")

    fig, ax = plt.subplots(figsize=(7, 4))
    sns.pointplot(data=df, x="pclass", y="survived", hue="embarked", errorbar=None, ax=ax)
    ax.set_ylabel("Survival rate")
    ax.set_title("Survival by class and embarkation port")
    savefig("story_4_class_embarked_survival.png")
    profile.append("\n## Chart interpretation 4 — class and embarkation\n\nSurvival rates still differ strongly by passenger class after separating the observations by embarkation port. Port-level differences should be read in the context of class composition, so this chart adds context to the main class pattern rather than establishing a causal effect of embarkation.")

    # Exploratory standardization sanity check.
    scaler = StandardScaler()
    scaled = pd.DataFrame(scaler.fit_transform(df[["age", "fare"]]), columns=["age_z", "fare_z"])
    standardization = pd.DataFrame({
        "before_mean": df[["age", "fare"]].mean(),
        "before_std": df[["age", "fare"]].std(ddof=0),
    })
    standardization["after_mean"] = scaled[["age_z", "fare_z"]].mean().to_numpy()
    standardization["after_std"] = scaled[["age_z", "fare_z"]].std(ddof=0).to_numpy()
    standardization.index = ["age", "fare"]
    profile.append("\n## Exploratory standardization check\n\n" + standardization.round(4).to_markdown())
    profile.append("\nThe transformed age and fare columns are approximately mean 0 and standard deviation 1. This is an EDA sanity check only; the modeling script fits its own preprocessing exclusively on the training split.")

    (OUT / "eda_report.md").write_text("\n".join(profile), encoding="utf-8")
    print("EDA complete:", OUT / "eda_report.md")


if __name__ == "__main__":
    main()
