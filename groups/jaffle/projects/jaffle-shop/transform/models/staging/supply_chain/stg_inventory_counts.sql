with

source as (

    select * from {{ source('supply_chain', 'raw_inventory_counts') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as inventory_count_id,
        cast(product_id as varchar) as product_id,
        cast(location_id as varchar) as location_id,

        ---------- numerics
        quantity_on_hand,
        quantity_reserved,
        quantity_available,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'counted_at') }} as counted_at

    from source

)

select * from renamed
