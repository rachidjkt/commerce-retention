select *
from {{ ref('fct_orders') }}
where gross_recorded_sales <= 0
   or gross_recorded_sales is null
   or recorded_units <= 0
   or recorded_units is null
   or recorded_line_count < 1
   or last_line_at < order_at
