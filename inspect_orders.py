from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent

with duckdb.connect(
    str(ROOT / "data/commerce.duckdb"),
    read_only=True,
) as con:

    print("ORDER SUMMARY")

    print(con.execute("""
        select
            count(*) as orders,
            count(distinct customer_id) as customers,
            min(order_at) as first_order,
            max(order_at) as last_order,
            round(avg(gross_recorded_sales), 2)
                as average_gross_order_value,
            round(median(gross_recorded_sales), 2)
                as median_gross_order_value
        from analytics.fct_orders
    """).df().to_string(index=False))

    print("\nLARGEST ORDERS")

    print(con.execute("""
        select
            order_id,
            customer_id,
            order_at,
            gross_recorded_sales
        from analytics.fct_orders
        order by gross_recorded_sales desc
        limit 5
    """).df().to_string(index=False))