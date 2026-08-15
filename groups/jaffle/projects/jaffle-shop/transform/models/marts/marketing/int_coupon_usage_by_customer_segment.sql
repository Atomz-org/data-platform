with

coupon_redemptions as (

    select * from {{ ref('fct_coupon_redemptions') }}

),

customers as (

    select * from {{ ref('customers') }}

),

-- Assign customer value segments based on lifetime spend
customer_segments as (

    select
        customer_id,
        customer_name,
        lifetime_spend,
        count_lifetime_orders,
        case
            when lifetime_spend is null or lifetime_spend = 0 then 'no_purchases'
            when lifetime_spend >= 500 then 'high_value'
            when lifetime_spend >= 200 then 'medium_value'
            when lifetime_spend >= 50 then 'low_value'
            else 'minimal_value'
        end as customer_segment

    from customers

),

-- Join redemptions with customer segments
redemption_with_segment as (

    select
        coupon_redemptions.redemption_id,
        coupon_redemptions.coupon_id,
        coupon_redemptions.coupon_code,
        coupon_redemptions.order_id,
        coupon_redemptions.customer_id,
        coupon_redemptions.discount_applied,
        coupon_redemptions.order_total,
        coupon_redemptions.net_order_total,
        customer_segments.customer_segment,
        customer_segments.lifetime_spend

    from coupon_redemptions

    inner join customer_segments
        on coupon_redemptions.customer_id = customer_segments.customer_id

),

-- Aggregate by segment
segment_summary as (

    select
        customer_segment,
        count(redemption_id) as total_redemptions,
        count(distinct customer_id) as unique_customers,
        sum(discount_applied) as total_discount_given,
        sum(order_total) as total_order_revenue,
        sum(net_order_total) as total_net_revenue,
        avg(discount_applied) as avg_discount_per_redemption,
        avg(order_total) as avg_order_value,
        -- Redemptions per customer in segment
        case
            when count(distinct customer_id) > 0
            then count(redemption_id) * 1.0 / count(distinct customer_id)
            else 0
        end as redemptions_per_customer

    from redemption_with_segment
    group by 1

)

select * from segment_summary
