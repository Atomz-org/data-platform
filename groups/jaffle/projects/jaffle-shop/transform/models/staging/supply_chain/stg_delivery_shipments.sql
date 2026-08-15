with

source as (

    select * from {{ source('supply_chain', 'raw_delivery_shipments') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as shipment_id,
        cast(purchase_order_id as varchar) as purchase_order_id,
        cast(supplier_id as varchar) as supplier_id,
        cast(destination_id as varchar) as destination_id,

        ---------- text
        destination_type,
        carrier,
        tracking_number,
        shipment_status,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'shipped_at') }} as shipped_at,
        {{ dbt.date_trunc('day', 'estimated_arrival_at') }} as estimated_arrival_at,
        {{ dbt.date_trunc('day', 'actual_arrival_at') }} as actual_arrival_at

    from source

)

select * from renamed
