with

source as (

    select * from {{ source('supply_chain', 'raw_purchase_orders') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as purchase_order_id,
        cast(supplier_id as varchar) as supplier_id,
        cast(warehouse_id as varchar) as warehouse_id,

        ---------- text
        status as po_status,

        ---------- numerics
        {{ cents_to_dollars('total_amount') }} as total_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'ordered_at') }} as ordered_at,
        {{ dbt.date_trunc('day', 'expected_delivery_at') }} as expected_delivery_at,
        {{ dbt.date_trunc('day', 'created_at') }} as created_at

    from source

)

select * from renamed
