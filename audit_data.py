from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent

df = pd.read_excel(ROOT / "data/raw/Online Retail.xlsx")

# These are identifiers, so preserve letters such as cancellation prefixes.
df["InvoiceNo"] = df["InvoiceNo"].astype("string")
df["StockCode"] = df["StockCode"].astype("string")

with duckdb.connect() as con:
    con.register("retail", df)

    def check(title, sql):
        print(f"\n--- {title} ---")
        print(con.execute(sql).df().to_string(index=False))

    check("1. Dataset overview", """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT InvoiceNo) AS invoices,
            COUNT(DISTINCT CustomerID) AS identified_customers,
            COUNT(DISTINCT StockCode) AS stock_codes,
            MIN(InvoiceDate) AS first_date,
            MAX(InvoiceDate) AS last_date
        FROM retail
    """)

    check("2. Missing values", """
        SELECT
            COUNT(*) FILTER (WHERE InvoiceNo IS NULL) AS missing_invoice,
            COUNT(*) FILTER (WHERE StockCode IS NULL) AS missing_stock_code,
            COUNT(*) FILTER (
                WHERE Description IS NULL OR TRIM(Description) = ''
            ) AS missing_description,
            COUNT(*) FILTER (WHERE CustomerID IS NULL) AS missing_customer,
            COUNT(*) FILTER (WHERE InvoiceDate IS NULL) AS missing_date,
            COUNT(*) FILTER (WHERE Quantity IS NULL) AS missing_quantity,
            COUNT(*) FILTER (WHERE UnitPrice IS NULL) AS missing_price,
            COUNT(*) FILTER (
                WHERE Country IS NULL OR TRIM(Country) = ''
            ) AS missing_country
        FROM retail
    """)

    check("3. Quantities, prices, and cancellation markers", """
        SELECT
            COUNT(*) FILTER (WHERE Quantity < 0) AS negative_quantity,
            COUNT(*) FILTER (WHERE Quantity = 0) AS zero_quantity,
            COUNT(*) FILTER (WHERE UnitPrice < 0) AS negative_price,
            COUNT(*) FILTER (WHERE UnitPrice = 0) AS zero_price,
            COUNT(*) FILTER (
                WHERE UPPER(InvoiceNo) LIKE 'C%'
            ) AS cancellation_rows,
            MIN(Quantity) AS min_quantity,
            MAX(Quantity) AS max_quantity,
            MIN(UnitPrice) AS min_price,
            MAX(UnitPrice) AS max_price
        FROM retail
    """)

    check("4. Exact duplicate rows", """
        SELECT COUNT(*) - (
            SELECT COUNT(*)
            FROM (SELECT DISTINCT * FROM retail) AS unique_rows
        ) AS duplicate_rows_beyond_first
        FROM retail
    """)

    check("5. Possible invoice inconsistencies", """
        SELECT
            InvoiceNo,
            COUNT(DISTINCT CustomerID) AS customers,
            COUNT(DISTINCT Country) AS countries,
            COUNT(DISTINCT InvoiceDate) AS timestamps
        FROM retail
        GROUP BY InvoiceNo
        HAVING COUNT(DISTINCT CustomerID) > 1
            OR COUNT(DISTINCT Country) > 1
            OR COUNT(DISTINCT InvoiceDate) > 1
        ORDER BY InvoiceNo
        LIMIT 10
    """)

    check("6. Largest absolute line amounts", """
        SELECT
            InvoiceNo,
            StockCode,
            Description,
            Quantity,
            UnitPrice,
            ROUND(Quantity * UnitPrice, 2) AS line_amount
        FROM retail
        ORDER BY ABS(Quantity * UnitPrice) DESC
        LIMIT 10
    """)
    check("7. Invoice timestamp differences", """
        SELECT
            InvoiceNo,
            MIN(InvoiceDate) AS first_timestamp,
            MAX(InvoiceDate) AS last_timestamp,
            MAX(InvoiceDate) - MIN(InvoiceDate) AS time_difference,
            COUNT(*) AS line_count
        FROM retail
        GROUP BY InvoiceNo
        HAVING COUNT(DISTINCT InvoiceDate) > 1
        ORDER BY time_difference DESC
        LIMIT 10
    """)

    check("8. Negative quantities without cancellation prefix", """
        SELECT
            StockCode,
            Description,
            COUNT(*) AS affected_rows,
            SUM(Quantity) AS total_quantity
        FROM retail
        WHERE Quantity < 0
          AND UPPER(InvoiceNo) NOT LIKE 'C%'
        GROUP BY StockCode, Description
        ORDER BY affected_rows DESC
        LIMIT 15
    """)