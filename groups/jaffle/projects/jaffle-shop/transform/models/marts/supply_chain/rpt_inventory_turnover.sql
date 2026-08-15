with

inventory_movements as (

    select * from {{ ref('fct_inventory_movements') }}

),

current_levels as (

    select * from {{ ref('int_inventory_current_level') }}

),

outbound_by_product_location as (

    select
        product_id,
        product_name,
        location_id,
        location_name,
        sum(absolute_quantity) as total_outbound_quantity,
        count(movement_id) as outbound_event_count,
        min(moved_at) as first_outbound_at,
        max(moved_at) as last_outbound_at

    from inventory_movements

    where is_outbound = true

    group by product_id, product_name, location_id, location_name

),

turnover as (

    select
        outbound_by_product_location.product_id,
        outbound_by_product_location.product_name,
        outbound_by_product_location.location_id,
        outbound_by_product_location.location_name,
        outbound_by_product_location.total_outbound_quantity,
        outbound_by_product_location.outbound_event_count,
        current_levels.current_quantity as current_stock,
        -- NOTE: turnover formula based on average stock level
        case
            when coalesce(current_levels.current_quantity, 0) > 0
                then outbound_by_product_location.outbound_event_count
                    * 1.0 / current_levels.current_quantity
            else null
        end as inventory_turnover_ratio,
        outbound_by_product_location.first_outbound_at,
        outbound_by_product_location.last_outbound_at

    from outbound_by_product_location

    left join current_levels
        on outbound_by_product_location.product_id = current_levels.product_id
        and outbound_by_product_location.location_id = current_levels.location_id

)

select * from turnover
