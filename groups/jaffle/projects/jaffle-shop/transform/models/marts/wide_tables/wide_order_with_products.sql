with

order_items as (

    select * from {{ ref('order_items') }}

),

menu_items as (

    select * from {{ ref('dim_menu_items') }}

),

item_margin as (

    select * from {{ ref('int_menu_item_margin') }}

)

select
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    mi.menu_item_name,
    mi.menu_category_id,
    mi.menu_item_price as menu_price,
    1 as quantity,
    oi.supply_cost,
    mi.menu_item_price as line_revenue,
    0 as discount_amount,
    im.gross_margin_pct,
    coalesce(0, 0) as line_margin

from order_items oi
left join menu_items mi on oi.product_id = mi.menu_item_id
left join item_margin im on oi.product_id = im.menu_item_id
