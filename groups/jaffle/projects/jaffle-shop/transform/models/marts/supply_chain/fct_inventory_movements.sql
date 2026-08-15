with

inventory_movements as (

    select * from {{ ref('stg_inventory_movements') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        inventory_movements.movement_id,
        inventory_movements.product_id,
        products.product_name,
        products.product_type,
        inventory_movements.location_id,
        locations.location_name,
        inventory_movements.movement_type,
        inventory_movements.reference_type,
        inventory_movements.reference_id,
        inventory_movements.quantity,
        abs(inventory_movements.quantity) as absolute_quantity,
        case
            when inventory_movements.movement_type = 'inbound' then true
            else false
        end as is_inbound,
        case
            when inventory_movements.movement_type = 'outbound' then true
            else false
        end as is_outbound,
        inventory_movements.moved_at

    from inventory_movements

    left join products
        on inventory_movements.product_id = products.product_id

    left join locations
        on inventory_movements.location_id = locations.location_id

)

select * from final
