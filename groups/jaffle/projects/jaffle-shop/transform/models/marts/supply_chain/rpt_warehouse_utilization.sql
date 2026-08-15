with

warehouses as (

    select * from {{ ref('dim_warehouses') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

warehouse_inventory as (

    select
        location_id as warehouse_id,
        count(distinct product_id) as distinct_products_stored,
        sum(current_quantity) as total_units_stored,
        sum(total_inbound) as lifetime_inbound,
        sum(total_outbound) as lifetime_outbound,
        sum(total_movements) as lifetime_movements,
        max(last_movement_at) as last_activity_at

    from current_levels

    group by location_id

),

utilization as (

    select
        warehouses.warehouse_id,
        warehouses.warehouse_name,
        warehouses.city,
        warehouses.state,
        warehouses.warehouse_type,
        warehouses.capacity_units,
        warehouses.is_active,
        warehouses.opened_at,
        coalesce(warehouse_inventory.distinct_products_stored, 0) as distinct_products_stored,
        coalesce(warehouse_inventory.total_units_stored, 0) as total_units_stored,
        case
            when warehouses.capacity_units > 0
                then coalesce(warehouse_inventory.total_units_stored, 0) * 1.0
                    / warehouses.capacity_units
            else null
        end as utilization_rate,
        case
            when warehouses.capacity_units > 0
                then warehouses.capacity_units
                    - coalesce(warehouse_inventory.total_units_stored, 0)
            else null
        end as available_capacity,
        coalesce(warehouse_inventory.lifetime_inbound, 0) as lifetime_inbound,
        coalesce(warehouse_inventory.lifetime_outbound, 0) as lifetime_outbound,
        warehouse_inventory.last_activity_at

    from warehouses

    left join warehouse_inventory
        on warehouses.warehouse_id = warehouse_inventory.warehouse_id

)

select * from utilization
