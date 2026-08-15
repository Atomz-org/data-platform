with

il as (
    select * from {{ ref('int_inventory_current_level') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

warehouses as (

    select
        warehouse_id,
        warehouse_name,
        capacity_units
    from {{ ref('stg_warehouses') }}
    where is_active

),

inventory_levels as (

    select
        il.location_id,
        il.product_id,
        il.current_quantity,
        coalesce(p.product_price, 0) as unit_price
    from il
    left join p on il.product_id = p.product_id

),

inventory_by_warehouse as (

    select
        location_id as warehouse_id,
        count(distinct product_id) as distinct_products,
        sum(current_quantity) as total_units_stored,
        sum(current_quantity * unit_price) as total_inventory_value
    from inventory_levels
    group by 1

),

final as (

    select
        w.warehouse_id,
        w.warehouse_name,
        w.capacity_units,
        coalesce(iw.distinct_products, 0) as distinct_products,
        coalesce(iw.total_units_stored, 0) as total_units_stored,
        coalesce(iw.total_inventory_value, 0) as total_inventory_value,
        case
            when w.capacity_units > 0
                then round(coalesce(iw.total_units_stored, 0) * 100.0 / w.capacity_units, 2)
            else 0
        end as capacity_utilization_pct,
        case
            when coalesce(iw.total_units_stored, 0) > 0
                then round(iw.total_inventory_value / iw.total_units_stored, 2)
            else 0
        end as avg_value_per_unit
    from warehouses as w
    left join inventory_by_warehouse as iw
        on w.warehouse_id = iw.warehouse_id

)

select * from final
