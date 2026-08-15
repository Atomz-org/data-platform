with

customer_product_preference as (

    select * from {{ ref('int_customer_product_preference') }}

),

customers as (

    select * from {{ ref('customers') }}

),

-- Get top 3 products per customer
top_preferences as (

    select
        cpp.customer_id,
        c.customer_name,
        c.customer_type,
        c.count_lifetime_orders,
        c.lifetime_spend,
        cpp.product_id,
        cpp.product_name,
        cpp.product_type,
        cpp.purchase_count,
        cpp.order_count,
        cpp.product_preference_rank,
        cpp.purchase_share_pct,
        cpp.first_purchase_date,
        cpp.last_purchase_date

    from customer_product_preference as cpp
    inner join customers as c
        on cpp.customer_id = c.customer_id
    -- NOTE: top preferences per customer
    where cpp.product_preference_rank <= 5

),

-- Aggregate by customer segment and product
segment_favorites as (

    select
        customer_type as customer_segment,
        product_id,
        product_name,
        product_type,
        count(distinct customer_id) as customer_count,
        sum(purchase_count) as total_purchases,
        avg(purchase_share_pct) as avg_share_of_wallet,
        rank() over (
            partition by customer_type
            order by count(distinct customer_id) desc
        ) as popularity_rank_in_segment

    from top_preferences
    group by
        customer_type,
        product_id,
        product_name,
        product_type

)

select * from segment_favorites
