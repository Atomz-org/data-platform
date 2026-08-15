with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

daily_product_orders as (

    select
        o.ordered_at as order_date,
        oi.product_id,
        any_value(p.product_name) as product_name,
        any_value(p.product_type) as product_type,
        count(oi.order_item_id) as units_sold,
        count(distinct oi.order_id) as order_count,
        count(oi.order_item_id) * any_value(p.product_price) as daily_revenue

    from order_items as oi

    inner join orders as o
        on oi.order_id = o.order_id

    inner join products as p
        on oi.product_id = p.product_id

    group by 1, 2

)

select * from daily_product_orders
