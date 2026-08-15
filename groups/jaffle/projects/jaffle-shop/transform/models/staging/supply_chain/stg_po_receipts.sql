with

source as (

    select * from {{ source('supply_chain', 'raw_po_receipts') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as receipt_id,
        cast(purchase_order_id as varchar) as purchase_order_id,
        cast(po_line_item_id as varchar) as po_line_item_id,

        ---------- numerics
        quantity_received,

        ---------- text
        quality_status,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'received_at') }} as received_at

    from source

)

select * from renamed
