# Commerce retention: 30-day repeat purchasing

Predict whether an identified existing customer places another recorded positive order within 30 days. This project turns transaction records into auditable customer snapshots and compares a constant baseline, recency-only logistic regression, and full logistic regression using chronological validation.

The implementation covers source-row traceability, SQL quality flags, positive-order aggregation, customer snapshots with historical cutoffs, and scikit-learn model comparison. It provides an auditable ranking of repeat-purchase propensity for customer prioritization.

**Stack:** Python, SQL, DuckDB, dbt, pandas, scikit-learn.

```text
Excel -> raw.retail -> stg_retail -> fct_orders -> customer_snapshots
      -> training/validation -> final evaluation
```

The input contains 541,909 transaction records. The orders table contains 18,532 positive recorded orders from 4,338 identified customers. The selected model achieved test average precision of 0.5477; the completed run reported 2.08x ranking lift in the highest-scored 20%.

## Setup and execution

Run from the repository root in PowerShell with Python 3.12 (the existing environment uses 3.12.10). All project paths below are relative.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
New-Item -ItemType Directory -Force data/raw | Out-Null
Invoke-WebRequest -Uri 'https://archive.ics.uci.edu/static/public/352/online+retail.zip' -OutFile data/raw/online-retail.zip
Expand-Archive -LiteralPath data/raw/online-retail.zip -DestinationPath data/raw -Force
.\.venv\Scripts\python.exe audit_data.py
.\.venv\Scripts\python.exe ingest.py
.\.venv\Scripts\dbt.exe build --profiles-dir .
.\.venv\Scripts\python.exe inspect_orders.py
.\.venv\Scripts\python.exe inspect_snapshots.py
```

The expected workbook is `data/raw/Online Retail.xlsx`. Ingestion replaces `raw.retail` rather than appending; dbt creates one staging view and two mart tables in the local `data/commerce.duckdb` database. `profiles.yml` is a portable local DuckDB profile without credentials. Close other database writers before building.

For a deliberate reproduction of the completed modeling experiment, after building the data:

```powershell
.\.venv\Scripts\python.exe train_model.py
.\.venv\Scripts\python.exe evaluate_test.py
```

These commands deliberately reproduce the experiment and overwrite model/evaluation artifacts. Training fits only training snapshots and scores validation; final evaluation loads the selected full logistic model and constant baseline without refitting. Saved models and customer-level predictions are excluded from Git, so a new checkout requires training before evaluation. To review existing results, use the committed aggregate CSVs without rerunning the holdout.

`requirements.txt` is the complete UTF-8 `pip freeze` from this project's existing `.venv`, including transitive and unused installed packages. It contains no local dependency paths. A fresh installation was not tested.

## Dataset and quality rules

[UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online-retail) ([ZIP download](https://archive.ics.uci.edu/static/public/352/online+retail.zip)) contains transactions from December 1, 2010 through December 9, 2011 for a UK retailer. Citation: Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [doi:10.24432/C5BW33](https://doi.org/10.24432/C5BW33). Dataset license: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The dataset is downloaded separately and is not committed.

The following counts were checked against the existing database; categories overlap:

| Finding | Records | Implemented handling |
| --- | ---: | --- |
| Missing customer ID | 135,080 | Retained in staging; excluded from orders and retention modeling |
| Missing/blank description | 1,454 | Trimmed and converted to NULL; no description-based exclusion |
| Negative quantity | 10,624 | Flagged; excluded from positive sale lines |
| Zero quantity | 0 | Positive sale rule requires quantity > 0 |
| Negative price | 2 | Excluded from positive sale lines |
| Zero price | 2,515 | Excluded from positive sale lines |
| Cancellation-prefixed invoice | 9,288 | Case-insensitive `C` prefix flag; excluded from positive sale lines |
| Exact duplicate rows beyond first | 5,268 | Preserved with distinct source Excel row numbers |

Identifiers retain letters; customer IDs loaded as floats are converted to integer strings. Staging retains every source row. Eligible order lines require a customer ID, quantity > 0, price > 0, and no cancellation prefix. Orders group by invoice, customer, and country; sales sum eligible quantity times price. No deduplication, outlier clipping, or cancellation matching is performed.

There are 43 invoices with multiple timestamps, with a maximum gap of one minute. `order_at` is the earliest eligible line time and `last_line_at` the latest. Historical orders require `last_line_at < snapshot_date`, so all included positive lines precede the cutoff. This represents completed recorded positive activity, not a verified fulfillment status. UCI's page says there are no missing values; the workbook contains missing customer IDs and descriptions as shown above.

## Features and chronological evaluation

Each snapshot includes customers with at least one eligible order completed strictly before its date. Labels are 1 when an eligible order's `order_at` falls in **[snapshot date, snapshot date + 30 days)**, otherwise 0. Customer IDs and audit timestamps are not model inputs.

| Feature | Definition at the snapshot |
| --- | --- |
| `recency_days` | Calendar day difference from latest historical `last_line_at` |
| `observed_tenure_days` | Calendar day difference from first observed historical `order_at` |
| `historical_orders` | Count of all eligible historical orders |
| `orders_90d` | Historical orders whose `order_at` is at least snapshot minus 90 days |
| `gross_sales_90d` | Gross recorded sales of those 90-day orders; zero when absent |

| Split | Snapshot dates (2011) | Customer snapshots |
| --- | --- | ---: |
| Training | April 1 / May 1 / June 1 | 2,134 / 2,434 / 2,718 |
| Validation | August 1 | 3,148 |
| Final test | October 1 | 3,616 |

Training contains 7,286 snapshots of 2,718 unique customers. The same customer may appear at multiple dates. Training labels end before validation begins. All label windows fit inside the recorded data coverage.

The constant baseline predicts the training return prevalence. Both logistic models apply `log1p`, standardization, and logistic regression (`max_iter=1000`); transformations and coefficients are fitted on training only. Full logistic regression was selected using validation average precision. The evaluation script hardcodes that selected model alongside the baseline; training does not automatically select or refit a winner on validation.

## Results

Values below are rounded to four decimals from the saved aggregate CSVs; those files retain full precision. Higher ROC-AUC and average precision (AP) are better; lower Brier score is better.

| Split | Model | ROC-AUC | AP | Brier |
| --- | --- | ---: | ---: | ---: |
| Validation | Constant baseline | 0.5000 | 0.2379 | 0.1833 |
| Validation | Recency only | 0.7035 | 0.3879 | 0.1680 |
| Validation | Full logistic | 0.7673 | 0.5743 | 0.1516 |
| Final test | Constant baseline | 0.5000 | 0.2702 | 0.1973 |
| Final test | Full logistic | 0.7180 | 0.5477 | 0.1740 |

The completed run reported 724 customers in the highest-scored 20% (`ceil(0.20 * 3616)`), with a 56.08% observed return rate versus 27.02% overall: **2.08x ranking lift**. These rounded prioritization figures come from the completed-run notes; they are not stored in the aggregate metric CSVs and were not recalculated during packaging. No conflict was found between those notes, the saved aggregate metrics, and the checked data counts.

This predicts **purchasing propensity**, not the incremental effect of marketing. Labels describe observed purchases without treatment assignment or a control group. A high-scoring customer may return without contact; ranking lift does not establish marketing uplift, campaign ROI, or business savings.

## Verification

Initial publication checks on November 20 used the existing environment and database: six Python files passed syntax parsing, and `dbt build --profiles-dir .` built 3 models and passed 11 data tests. This documentation polish checked relative links and consistency with code and saved evidence; it did not rerun training, dbt, or final holdout evaluation. A fresh installation was not tested.

## Limitations

The data comes from one historical retailer and excludes customers without IDs from retention modeling. Possible duplicate source lines remain, and cancellations are not reconciled against purchases, so gross recorded sales are not net revenue. Customers recur across historical snapshots. Repeat-purchase labels do not establish marketing uplift, and there is no production deployment or measured business savings. Validation and test performance differ, so these results do not establish future performance.

## Attribution and licensing

The UCI dataset is attributed above and downloaded separately under CC BY 4.0. Python dependencies, DuckDB, dbt, pandas, and scikit-learn retain their own licenses. See [ATTRIBUTION.md](ATTRIBUTION.md) for source and dependency scope. No project-wide code license has been selected.
