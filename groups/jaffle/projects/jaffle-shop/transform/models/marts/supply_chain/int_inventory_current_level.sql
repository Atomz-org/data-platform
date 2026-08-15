with

inventory_movements as (

    select * from {{ ref('stg_inventory_movements') }}

),

running_inventory as (

    select
        product_id,
        location_id,
        sum(quantity) as current_quantity,
        sum(
            case
                when movement_type = 'inbound' then quantity
                else 0
            end
        ) as total_inbound,
        sum(
            case
                when movement_type = 'outbound' then abs(quantity)
                else 0
            end
        ) as total_outbound,
        max(moved_at) as last_movement_at,
        count(movement_id) as total_movements

    from inventory_movements

    group by product_id, location_id

)

select * from running_inventory
