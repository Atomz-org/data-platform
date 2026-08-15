with

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

po_line_items as (

    select * from {{ ref('stg_po_line_items') }}

),

latest_unit_cost as (

    select
        product_id,
        avg(unit_cost) as avg_unit_cost

    from po_line_items

    group by product_id

),

inventory_value as (

    select
        current_levels.product_id,
        current_levels.location_id,
        current_levels.current_quantity,
        coalesce(latest_unit_cost.avg_unit_cost, 0) as unit_cost,
        current_levels.current_quantity
            * coalesce(latest_unit_cost.avg_unit_cost, 0) as inventory_value,
        current_levels.last_movement_at

    from current_levels

    left join latest_unit_cost
        on current_levels.product_id = latest_unit_cost.product_id

)

select * from inventory_value
