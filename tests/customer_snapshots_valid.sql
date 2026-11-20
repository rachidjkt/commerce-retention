select *
from {{ ref('customer_snapshots') }}

where last_history_at >= snapshot_date
   or label_window_end > (
        select max(invoice_at)
        from {{ ref('stg_retail') }}
   )
   or recency_days < 0
   or observed_tenure_days < 0
   or historical_orders < 1
   or orders_90d > historical_orders
   or purchased_next_30d is null
   or purchased_next_30d not in (0, 1)