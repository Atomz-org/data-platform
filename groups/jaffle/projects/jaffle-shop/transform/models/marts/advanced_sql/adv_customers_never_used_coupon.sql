-- adv_customers_never_used_coupon.sql
-- Technique: NOT EXISTS anti-join pattern
-- Finds customers who have never redeemed a coupon. NOT EXISTS is a standard SQL
-- anti-join that short-circuits on the first match, making it efficient for
-- existence checks. This is preferred over LEFT JOIN / IS NULL for readability
-- and in some query planners for performance.

with customers as (

    select * from {{ ref('customers') }}

),

coupon_redemptions as (

    select * from {{ ref('fct_coupon_redemptions') }}

),

-- NOT EXISTS: return customers where no matching redemption row exists
customers_without_coupons as (

    select
        c.customer_id,
        c.customer_name,
        c.count_lifetime_orders,
        c.first_ordered_at,
        c.last_ordered_at,
        c.lifetime_spend

    from customers as c

    where not exists (
        select 1
        from coupon_redemptions as cr
        where cr.customer_id = c.customer_id
    )

)

select
    customer_id,
    customer_name,
    count_lifetime_orders,
    first_ordered_at,
    last_ordered_at,
    lifetime_spend,
    -- Business insight: high-spend customers who never used coupons
    -- are good candidates for targeted coupon campaigns
    case
        when lifetime_spend > 100 and count_lifetime_orders > 5
            then 'high_value_no_coupon'
        when count_lifetime_orders > 3
            then 'engaged_no_coupon'
        else 'low_engagement_no_coupon'
    end as coupon_opportunity_segment
from customers_without_coupons
order by lifetime_spend desc
