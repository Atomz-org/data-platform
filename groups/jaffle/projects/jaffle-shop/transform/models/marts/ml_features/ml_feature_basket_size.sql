with

orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select
        order_id,
        count(order_item_id) as item_count
    from {{ ref('stg_order_items') }}
    group by 1

),

customer_360 as (

    select
        customer_id,
        rfm_segment_code,
        loyalty_tier,
        ltv_tier
    from {{ ref('dim_customer_360') }}

),

date_spine as (

    select
        date_day,
        day_of_week,
        day_name,
        is_weekend
    from {{ ref('util_date_spine') }}

),

coupon_orders as (

    select distinct
        order_id,
        1 as has_coupon
    from {{ ref('fct_coupon_redemptions') }}

),

features as (

    select
        o.order_id,
        o.customer_id,
        o.location_id as store_id,
        o.ordered_at,
        o.order_total,
        o.subtotal,
        oi.item_count,

        -- Customer features
        coalesce(c.rfm_segment_code, 'unknown') as customer_rfm_segment,
        coalesce(c.loyalty_tier, 'none') as loyalty_tier,
        coalesce(c.ltv_tier, 'bronze') as ltv_tier,

        -- Temporal features
        ds.day_of_week,
        ds.day_name,
        ds.is_weekend,
        extract(month from o.ordered_at) as month_of_year,

        -- Promo features
        coalesce(co.has_coupon, 0) as promo_active,

        -- Target: basket size (item count)
        oi.item_count as basket_size

    from orders as o
    inner join order_items as oi
        on o.order_id = oi.order_id
    left join customer_360 as c
        on o.customer_id = c.customer_id
    left join date_spine as ds
        on o.ordered_at = ds.date_day
    left join coupon_orders as co
        on o.order_id = co.order_id

)

select * from features
