with

source as (

    select * from {{ source('supply_chain', 'raw_waste_logs') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as waste_log_id,
        cast(product_id as varchar) as product_id,
        cast(location_id as varchar) as location_id,

        ---------- text
        waste_reason,

        ---------- numerics
        quantity_wasted,
        {{ cents_to_dollars('cost_of_waste') }} as cost_of_waste,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'wasted_at') }} as wasted_at

    from source

)

select * from renamed
