with

warehouses as (

    select * from {{ ref('stg_warehouses') }}

),

final as (

    select
        warehouse_id,
        warehouse_name,
        address,
        city,
        state,
        warehouse_type,
        capacity_units,
        is_active,
        opened_at

    from warehouses

)

select * from final
