with

movements as (
    select * from {{ ref('stg_inventory_movements') }}
),

products as (
    select product_id, product_name, product_type from {{ ref('stg_products') }}
),

final as (
    select
        im.movement_id,
        im.product_id,
        p.product_name,
        p.product_type,
        im.location_id,
        im.moved_at,
        im.movement_type,
        im.quantity
    from movements as im
    left join products as p on im.product_id = p.product_id
)

select * from final
