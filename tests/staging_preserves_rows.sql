select
    (select count(*) from {{ source('retail_raw', 'retail') }})
        as raw_rows,

    (select count(*) from {{ ref('stg_retail') }})
        as staged_rows

where
    (select count(*) from {{ source('retail_raw', 'retail') }})
    <>
    (select count(*) from {{ ref('stg_retail') }})