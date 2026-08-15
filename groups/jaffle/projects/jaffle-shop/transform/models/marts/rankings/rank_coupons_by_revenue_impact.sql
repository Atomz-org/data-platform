with

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

o as (
    select * from {{ ref('stg_orders') }}
),

coupon_impact as (
    select
        cr.coupon_id,
        count(*) as redemptions,
        sum(cr.discount_applied) as total_discount,
        sum(o.order_total) as associated_revenue
    from cr
    inner join o on cr.order_id = o.order_id
    group by 1
),

ranked as (
    select
        coupon_id,
        redemptions,
        total_discount,
        associated_revenue,
        associated_revenue - total_discount as net_revenue_impact,
        rank() over (order by (associated_revenue - total_discount) desc) as revenue_impact_rank
    from coupon_impact
)

select * from ranked
