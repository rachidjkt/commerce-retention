from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent

with duckdb.connect(
    str(ROOT / "data/commerce.duckdb"),
    read_only=True,
) as con:

    result = con.execute("""
        select
            snapshot_date,
            dataset_split,
            count(*) as customers,
            sum(purchased_next_30d) as returning_customers,
            round(
                100.0 * avg(purchased_next_30d),
                2
            ) as repeat_purchase_pct
        from analytics.customer_snapshots
        group by snapshot_date, dataset_split
        order by snapshot_date
    """).df()

    print(result.to_string(index=False))