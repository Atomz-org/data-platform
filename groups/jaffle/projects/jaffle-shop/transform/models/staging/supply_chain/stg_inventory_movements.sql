with

source as (

    select * from {{ source('supply_chain', 'raw_inventory_movements') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as movement_id,
        cast(product_id as varchar) as product_id,
        cast(location_id as varchar) as location_id,

        ---------- text
        movement_type,
        reference_type,
        cast(reference_id as varchar) as reference_id,

        ---------- numerics
        quantity,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'moved_at') }} as moved_at

    from source

)

select * from renamed
