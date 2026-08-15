with 
o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

product_purchases as (
    select
        o.customer_id,
        oi.product_id,
        p.product_name,
        count(*) as purchase_count,
        sum(p.product_price) as product_spend
    from o
    inner join oi
        on o.order_id = oi.order_id
    inner join p
        on oi.product_id = p.product_id
    group by o.customer_id, oi.product_id, p.product_name
),

ranked_products as (
    select
        customer_id,
        product_id,
        product_name,
        purchase_count,
        product_spend,
        row_number() over (
            partition by customer_id
            order by purchase_count desc, product_spend desc
        ) as product_rank,
        sum(purchase_count) over (partition by customer_id) as total_items_purchased
    from product_purchases
),

top3 as (
    select
        customer_id,
        product_id,
        product_name,
        purchase_count,
        product_spend,
        product_rank,
        total_items_purchased,
        round(
            (cast(purchase_count as {{ dbt.type_float() }})
            / nullif(total_items_purchased, 0) * 100), 2
        ) as product_share_pct
    from ranked_products
    where product_rank <= 3
)

select
    customer_id,
    max(case when product_rank = 1 then product_id end) as top1_product_id,
    max(case when product_rank = 1 then product_name end) as top1_product_name,
    max(case when product_rank = 1 then purchase_count end) as top1_purchase_count,
    max(case when product_rank = 1 then product_share_pct end) as top1_product_share_pct,
    max(case when product_rank = 2 then product_id end) as top2_product_id,
    max(case when product_rank = 2 then product_name end) as top2_product_name,
    max(case when product_rank = 2 then purchase_count end) as top2_purchase_count,
    max(case when product_rank = 3 then product_id end) as top3_product_id,
    max(case when product_rank = 3 then product_name end) as top3_product_name,
    max(case when product_rank = 3 then purchase_count end) as top3_purchase_count,
    max(total_items_purchased) as total_items_purchased
from top3
group by customer_id
