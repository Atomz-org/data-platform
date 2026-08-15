with

items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select product_id, product_name, product_type, product_price from {{ ref('stg_products') }}
),

final as (
    select
        i.order_item_id,
        i.order_id,
        i.product_id,
        p.product_name,
        p.product_type,
        p.product_price as list_price
    from items as i
    left join products as p on i.product_id = p.product_id
)

select * from final
