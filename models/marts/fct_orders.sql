{{ config(materialized='table') }}

with eligible_lines as (

    select *
    from {{ ref('stg_retail') }}
    where is_positive_sale_row
      and customer_id is not null

)

select
    invoice_no as order_id,
    customer_id,
    country,

    min(invoice_at) as order_at,
    max(invoice_at) as last_line_at,

    count(*) as recorded_line_count,
    count(distinct stock_code) as distinct_stock_codes,
    sum(quantity) as recorded_units,
    sum(line_amount) as gross_recorded_sales

from eligible_lines

group by
    invoice_no,
    customer_id,
    country