from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data/raw/Online Retail.xlsx"
DATABASE = ROOT / "data/commerce.duckdb"

df = pd.read_excel(SOURCE)

# Preserve identifiers containing letters.
df["InvoiceNo"] = df["InvoiceNo"].astype("string")
df["StockCode"] = df["StockCode"].astype("string")

# Trace each record back to its original Excel row.
# Row 1 contains the column headings.
df.insert(0, "source_row_number", range(2, len(df) + 2))

with duckdb.connect(str(DATABASE)) as con:
    con.register("excel_data", df)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # Rebuild this raw table on reruns instead of appending duplicates.
    con.execute("""
        CREATE OR REPLACE TABLE raw.retail AS
        SELECT * FROM excel_data
    """)

    stored_rows = con.execute(
        "SELECT COUNT(*) FROM raw.retail"
    ).fetchone()[0]

    assert stored_rows == len(df), "Row count changed during ingestion"

    print(f"Loaded {stored_rows:,} rows into raw.retail")
    print(f"Database: {DATABASE}")

    print(con.execute("""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT source_row_number) AS unique_source_rows
        FROM raw.retail
    """).df().to_string(index=False))