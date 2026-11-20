from pathlib import Path

import duckdb
import pandas as pd
import numpy as np
import joblib

from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

root = Path(__file__).resolve().parent
artifacts = root / "artifacts"
artifacts.mkdir(exist_ok=True, parents=True)

FEATURES = ["recency_days","observed_tenure_days","historical_orders","orders_90d", "gross_sales_90d"]

Target = "purchased_next_30d"

with duckdb.connect(str(root / "data/commerce.duckdb"),read_only=True) as con:
    data = con.execute("""select * from analytics.customer_snapshots where dataset_split in ('train','validation') order by snapshot_date,customer_id""").df()



assert data["snapshot_id"].is_unique, "Duplicate customer snapshots"

train = data.loc[data["dataset_split"] == "train"].copy()
validation = data.loc[
    data["dataset_split"] == "validation"
].copy()

assert not train.empty and not validation.empty
assert train["snapshot_date"].max() < validation["snapshot_date"].min()
assert train["label_window_end"].max() <= validation["snapshot_date"].min()

for name, frame in [("train", train), ("validation", validation)]:
    values = frame[FEATURES].astype(float)

    assert np.isfinite(values.to_numpy()).all(), (
        f"Missing or infinite features in {name}"
    )
    assert (values >= 0).all().all(), (
        f"Negative feature values in {name}"
    )
    assert set(frame[Target].unique()) == {0, 1}, (
        f"Expected both outcome classes in {name}"
    )


def logistic_model():
    return make_pipeline(FunctionTransformer(np.log1p, validate=False), StandardScaler(), LogisticRegression(max_iter=1000))



experiments = [
    (
        "constant_baseline",
        DummyClassifier(strategy="prior"),
        FEATURES,
    ),
    (
        "recency_only",
        logistic_model(),
        ["recency_days"],
    ),
    (
        "full_logistic",
        logistic_model(),
        FEATURES,
    ),
]

results = []

for name, model, columns in experiments:
    x_train = train[columns].astype(float)
    x_validation = validation[columns].astype(float)

    # Preprocessing is fitted on training data only.
    model.fit(x_train, train[Target])

    probabilities = model.predict_proba(x_validation)[:, 1]
    actual = validation[Target].astype(int)

    results.append({
        "model": name,
        "roc_auc": roc_auc_score(actual, probabilities),
        "average_precision": average_precision_score(
            actual, probabilities
        ),
        "brier_score": brier_score_loss(actual, probabilities),
    })

    joblib.dump(
        {
            "model": model,
            "features": columns,
            "target": Target,
        },
        artifacts / f"{name}.joblib",
    )

results = pd.DataFrame(results)

results.to_csv(
    artifacts / "validation_metrics.csv",
    index=False,
)

print(f"Training snapshots: {len(train):,}")
print(f"Unique training customers: {train['customer_id'].nunique():,}")
print(f"Validation customers: {len(validation):,}")
print(f"Training return rate: {train[Target].mean():.2%}")
print(f"Validation return rate: {validation[Target].mean():.2%}")

print("\nVALIDATION RESULTS")
print(results.round(4).to_string(index=False))

print("\nSaved models and validation metrics in artifacts/")
