{{
    config(
        materialized='incremental',
        unique_key='order_item_id'
    )
}}

with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select order_id, ordered_at from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where ordered_at > (select max(ordered_at) from {{ this }})
    {% endif %}

),

products as (

    select * from {{ ref('stg_products') }}

),

supplies_by_product as (

    select product_id, sum(supply_cost) as supply_cost
    from {{ ref('stg_supplies') }}
    group by product_id

)

select
    oi.order_item_id,
    oi.order_id,
    o.ordered_at,
    oi.product_id,
    p.product_name,
    1 as quantity,
    coalesce(s.supply_cost, 0) as supply_cost,
    p.product_price as gross_item_revenue,
    p.product_price - coalesce(s.supply_cost, 0) as item_margin

from order_items oi
inner join orders o on oi.order_id = o.order_id
left join products p on oi.product_id = p.product_id
left join supplies_by_product s on oi.product_id = s.product_id
