with

source as (

    select * from {{ source('supply_chain', 'raw_warehouses') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as warehouse_id,

        ---------- text
        name as warehouse_name,
        address,
        city,
        state,
        warehouse_type,

        ---------- numerics
        capacity_units,

        ---------- booleans
        is_active,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'opened_at') }} as opened_at

    from source

)

select * from renamed
