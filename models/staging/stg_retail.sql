with standardized as (

    select
        source_row_number,
        trim(cast(InvoiceNo as varchar)) as invoice_no,
        trim(cast(StockCode as varchar)) as stock_code,
        nullif(trim(Description), '') as description,
        cast(Quantity as bigint) as quantity,
        cast(InvoiceDate as timestamp) as invoice_at,
        cast(UnitPrice as decimal(18, 4)) as unit_price,

        -- Excel loaded customer identifiers as floats.
        -- Convert 17850.0 to "17850", while preserving NULLs.
        cast(cast(CustomerID as bigint) as varchar) as customer_id,

        trim(Country) as country

    from {{ source('retail_raw', 'retail') }}

),

flagged as (

    select
        *,
        upper(invoice_no) like 'C%' as is_cancellation_invoice,
        quantity < 0 as has_negative_quantity,
        unit_price <= 0 as has_nonpositive_price,
        customer_id is null as is_missing_customer,

        quantity * unit_price as line_amount

    from standardized

)

select
    *,

    -- A candidate positive sale, not confirmed net revenue.
    (
        not is_cancellation_invoice
        and quantity > 0
        and unit_price > 0
    ) as is_positive_sale_row

from flagged