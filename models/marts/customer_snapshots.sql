{{ config(materialized='table') }}

with snapshot_dates as (

    select *
    from (
        values
            (date '2011-04-01', 'train'),
            (date '2011-05-01', 'train'),
            (date '2011-06-01', 'train'),
            (date '2011-08-01', 'validation'),
            (date '2011-10-01', 'test')
    ) as dates(snapshot_date, dataset_split)

),

history as (

    select
        s.snapshot_date,
        s.dataset_split,
        o.customer_id,

        min(o.order_at) as first_observed_order_at,
        max(o.last_line_at) as last_history_at,

        count(*) as historical_orders,

        count(*) filter (
            where o.order_at >= s.snapshot_date - interval '90 days'
        ) as orders_90d,

        coalesce(
            sum(o.gross_recorded_sales) filter (
                where o.order_at >= s.snapshot_date - interval '90 days'
            ),
            0
        ) as gross_sales_90d

    from snapshot_dates s

    join {{ ref('fct_orders') }} o
        -- All lines in a historical order must precede the cutoff.
        on o.last_line_at < s.snapshot_date

    group by
        s.snapshot_date,
        s.dataset_split,
        o.customer_id

)

select
    customer_id || '_' || cast(snapshot_date as varchar)
        as snapshot_id,

    customer_id,
    snapshot_date,
    dataset_split,

    date_diff(
        'day', last_history_at, snapshot_date
    ) as recency_days,

    date_diff(
        'day', first_observed_order_at, snapshot_date
    ) as observed_tenure_days,

    historical_orders,
    orders_90d,
    gross_sales_90d,

    -- Retained for auditing, not as an ML input.
    last_history_at,

    snapshot_date + interval '30 days' as label_window_end,

    cast(
        exists (
            select 1
            from {{ ref('fct_orders') }} future_order

            where future_order.customer_id = history.customer_id
              and future_order.order_at >= history.snapshot_date
              and future_order.order_at
                    < history.snapshot_date + interval '30 days'
        )
        as integer
    ) as purchased_next_30d

from history