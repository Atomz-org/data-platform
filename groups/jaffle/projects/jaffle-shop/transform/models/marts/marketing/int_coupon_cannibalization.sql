with

coupon_redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Get each customer's order history to identify repeat customers
customer_order_history as (

    select
        customer_id,
        order_id,
        ordered_at,
        order_total,
        row_number() over (
            partition by customer_id
            order by ordered_at asc
        ) as customer_order_sequence

    from orders

),

-- Join redemptions with customer order history
redemption_context as (

    select
        coupon_redemptions.redemption_id,
        coupon_redemptions.coupon_id,
        coupon_redemptions.order_id,
        coupon_redemptions.customer_id,
        coupon_redemptions.discount_applied,
        coupon_redemptions.redeemed_at,
        customer_order_history.order_total,
        customer_order_history.customer_order_sequence,
        -- A repeat customer (order_sequence > 1) likely would have purchased anyway
        case
            when customer_order_history.customer_order_sequence > 1 then true
            else false
        end as is_likely_cannibalized

    from coupon_redemptions

    inner join customer_order_history
        on coupon_redemptions.order_id = customer_order_history.order_id
        and coupon_redemptions.customer_id = customer_order_history.customer_id

),

-- Summarize cannibalization metrics by coupon
coupon_cannibalization as (

    select
        coupon_id,
        count(redemption_id) as total_redemptions,
        sum(case when is_likely_cannibalized then 1 else 0 end) as cannibalized_redemptions,
        sum(case when not is_likely_cannibalized then 1 else 0 end) as incremental_redemptions,
        case
            when count(redemption_id) > 0
            then sum(case when is_likely_cannibalized then 1 else 0 end) * 1.0 / count(redemption_id)
            else 0
        end as cannibalization_rate,
        sum(case when is_likely_cannibalized then discount_applied else 0 end) as cannibalized_discount_cost,
        sum(case when not is_likely_cannibalized then discount_applied else 0 end) as incremental_discount_cost,
        sum(order_total) as total_order_revenue,
        sum(discount_applied) as total_discount_cost

    from redemption_context
    group by 1

)

select * from coupon_cannibalization
