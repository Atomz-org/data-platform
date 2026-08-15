with

movements as (

    select * from {{ ref('fct_inventory_movements') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

daily_movements as (

    select
        {{ dbt.date_trunc('day', 'moved_at') }} as movement_date,
        location_id,
        location_name,
        count(movement_id) as total_movements,
        sum(case when is_inbound then absolute_quantity else 0 end) as inbound_quantity,
        sum(case when is_outbound then absolute_quantity else 0 end) as outbound_quantity,
        count(distinct product_id) as distinct_products_moved

    from movements
    group by 1, 2, 3

),

warehouse_inventory_value as (

    select
        location_id,
        count(distinct product_id) as products_in_stock,
        sum(current_quantity) as total_units_on_hand,
        sum(total_movements) as lifetime_movements

    from current_levels
    group by location_id

),

final as (

    select
        dm.movement_date,
        dm.location_id,
        dm.location_name,
        dm.total_movements,
        dm.inbound_quantity,
        dm.outbound_quantity,
        dm.distinct_products_moved,
        coalesce(wiv.products_in_stock, 0) as products_in_stock,
        coalesce(wiv.total_units_on_hand, 0) as total_units_on_hand

    from daily_movements as dm

    left join warehouse_inventory_value as wiv
        on dm.location_id = wiv.location_id

)

select * from final
