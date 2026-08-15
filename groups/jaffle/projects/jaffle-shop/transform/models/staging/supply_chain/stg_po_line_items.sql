with

source as (

    select * from {{ source('supply_chain', 'raw_po_line_items') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as po_line_item_id,
        cast(purchase_order_id as varchar) as purchase_order_id,
        cast(product_id as varchar) as product_id,

        ---------- numerics
        quantity_ordered,
        {{ cents_to_dollars('unit_cost') }} as unit_cost,
        {{ cents_to_dollars('line_total') }} as line_total

    from source

)

select * from renamed
