with

movements as (

    select * from {{ ref('stg_inventory_movements') }}

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

final as (

    select
        m.movement_id,
        m.product_id,
        p.product_name,
        p.product_type,
        m.location_id,
        l.location_name,
        m.movement_type,
        m.reference_type,
        m.reference_id,
        m.quantity,
        abs(m.quantity) as absolute_quantity,
        m.moved_at,
        case
            when m.movement_type = 'inbound' then abs(m.quantity)
            else 0
        end as inbound_quantity,
        case
            when m.movement_type = 'outbound' then abs(m.quantity)
            else 0
        end as outbound_quantity
    from movements as m
    left join products as p
        on m.product_id = p.product_id
    left join locations as l
        on m.location_id = l.location_id

)

select * from final
