from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"

with duckdb.connect(
    str(ROOT / "data/commerce.duckdb"),
    read_only=True,
) as con:
    test = con.execute("""
        select *
        from analytics.customer_snapshots
        where dataset_split = 'test'
        order by customer_id
    """).df()

assert not test.empty
assert test["snapshot_id"].is_unique
assert set(test["purchased_next_30d"].unique()) == {0, 1}

actual = test["purchased_next_30d"].astype(int)

results = []
full_probabilities = None

# Selection was made using validation data.
# The constant model remains a reference baseline.
for name in ["constant_baseline", "full_logistic"]:
    bundle = joblib.load(ARTIFACTS / f"{name}.joblib")

    features = test[bundle["features"]].astype(float)
    assert np.isfinite(features.to_numpy()).all()

    # No fitting or preprocessing refitting on test data.
    probabilities = bundle["model"].predict_proba(features)[:, 1]

    results.append({
        "model": name,
        "roc_auc": roc_auc_score(actual, probabilities),
        "average_precision": average_precision_score(
            actual, probabilities
        ),
        "brier_score": brier_score_loss(actual, probabilities),
    })

    if name == "full_logistic":
        full_probabilities = probabilities

results = pd.DataFrame(results)
results.to_csv(ARTIFACTS / "test_metrics.csv", index=False)

# Illustrative prioritization policy, fixed before viewing results:
# inspect the highest-scored 20% of customers.
top_count = int(np.ceil(0.20 * len(test)))
top_positions = np.argsort(
    -full_probabilities,
    kind="stable",
)[:top_count]

top_precision = actual.iloc[top_positions].mean()
overall_rate = actual.mean()

predictions = test[
    ["snapshot_id", "customer_id", "snapshot_date"]
].copy()

predictions["actual_return"] = actual.to_numpy()
predictions["predicted_return_probability"] = full_probabilities

predictions.to_csv(
    ARTIFACTS / "test_predictions.csv",
    index=False,
)

print(f"Test customers: {len(test):,}")
print(f"Observed return rate: {overall_rate:.2%}")

print("\nFINAL TEST RESULTS")
print(results.round(4).to_string(index=False))

print(f"\nCustomers in highest-scored 20%: {top_count:,}")
print(f"Return rate within that group: {top_precision:.2%}")
print(f"Ranking lift over overall rate: {top_precision / overall_rate:.2f}x")

print("\nSaved test metrics and predictions in artifacts/")