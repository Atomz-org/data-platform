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

customer_product_orders as (

    select
        o.customer_id,
        oi.product_id,
        p.product_name,
        p.product_type,
        count(oi.order_item_id) as purchase_count,
        count(distinct oi.order_id) as order_count,
        min(o.ordered_at) as first_purchase_date,
        max(o.ordered_at) as last_purchase_date

    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id
    inner join products as p
        on oi.product_id = p.product_id
    group by
        o.customer_id,
        oi.product_id,
        p.product_name,
        p.product_type

),

ranked as (

    select
        customer_id,
        product_id,
        product_name,
        product_type,
        purchase_count,
        order_count,
        first_purchase_date,
        last_purchase_date,
        rank() over (
            partition by customer_id
            order by purchase_count desc
        ) as product_preference_rank,
        purchase_count * 1.0 / nullif(
            sum(purchase_count) over (partition by customer_id), 0
        ) as purchase_share_pct

    from customer_product_orders

)

select * from ranked
