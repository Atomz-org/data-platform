with monthly as (
    select
        {{ sf_date_trunc('month', "redeemed_at") }} as redemption_month,
        count(*) as redemptions,
        sum(discount_applied) as total_discount
    from {{ ref('fct_coupon_redemptions') }}
    group by 1
),
orders as (
    select
        {{ sf_date_trunc('month', "ordered_at") }} as order_month,
        count(*) as total_orders
    from {{ ref('stg_orders') }}
    group by 1
),
final as (
    select
        o.order_month,
        coalesce(m.redemptions, 0) as redemptions,
        o.total_orders,
        round(coalesce(m.redemptions, 0) * 100.0 / nullif(o.total_orders, 0), 2) as redemption_rate_pct,
        coalesce(m.total_discount, 0) as total_discount
    from orders as o
    left join monthly as m on o.order_month = m.redemption_month
)
select * from final
