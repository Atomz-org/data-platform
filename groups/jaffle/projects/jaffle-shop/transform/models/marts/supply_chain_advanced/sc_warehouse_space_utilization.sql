with

warehouses as (

    select
        warehouse_id,
        warehouse_name,
        capacity_units,
        warehouse_type,
        is_active
    from {{ ref('dim_warehouses') }}
    where is_active = true

),

inventory as (

    select
        location_id,
        sum(current_quantity) as total_units_stored
    from {{ ref('int_inventory_current_level') }}
    group by 1

),

final as (

    select
        w.warehouse_id,
        w.warehouse_name,
        w.warehouse_type,
        w.capacity_units,
        coalesce(inv.total_units_stored, 0) as current_units_stored,
        case
            when w.capacity_units > 0
            then cast(coalesce(inv.total_units_stored, 0) as {{ dbt.type_float() }})
                / w.capacity_units * 100
            else 0
        end as utilization_pct,
        w.capacity_units - coalesce(inv.total_units_stored, 0) as available_capacity,
        case
            when w.capacity_units > 0
                and cast(coalesce(inv.total_units_stored, 0) as {{ dbt.type_float() }}) / w.capacity_units > 0.90
            then 'critical'
            when w.capacity_units > 0
                and cast(coalesce(inv.total_units_stored, 0) as {{ dbt.type_float() }}) / w.capacity_units > 0.75
            then 'high'
            when w.capacity_units > 0
                and cast(coalesce(inv.total_units_stored, 0) as {{ dbt.type_float() }}) / w.capacity_units > 0.50
            then 'moderate'
            else 'low'
        end as utilization_level
    from warehouses as w
    left join inventory as inv on w.warehouse_id = inv.location_id

)

select * from final
