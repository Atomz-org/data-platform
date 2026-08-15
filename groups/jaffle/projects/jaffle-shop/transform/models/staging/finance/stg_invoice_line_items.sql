with

source as (

    select * from {{ source('finance', 'raw_invoice_line_items') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as invoice_line_item_id,
        cast(invoice_id as varchar) as invoice_id,
        cast(product_id as varchar) as product_id,

        ---------- text
        description as line_item_description,

        ---------- numerics
        quantity,
        {{ cents_to_dollars('unit_price') }} as unit_price,
        {{ cents_to_dollars('line_total') }} as line_total

    from source

)

select * from renamed
