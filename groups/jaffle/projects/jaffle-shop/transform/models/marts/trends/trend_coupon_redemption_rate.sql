with

daily_coupons as (
    select
        redeemed_at,
        count(*) as redemptions,
        sum(discount_applied) as total_discount
    from {{ ref('fct_coupon_redemptions') }}
    group by 1
),

daily_orders as (
    select
        ordered_at as order_date,
        count(*) as total_orders
    from {{ ref('stg_orders') }}
    group by 1
),

combined as (
    select
        daily_ord.order_date as metric_date,
        coalesce(dc.redemptions, 0) as redemptions,
        daily_ord.total_orders,
        round(coalesce(dc.redemptions, 0) * 100.0 / nullif(daily_ord.total_orders, 0), 2) as redemption_rate_pct,
        coalesce(dc.total_discount, 0) as total_discount
    from daily_orders as daily_ord
    left join daily_coupons as dc on daily_ord.order_date = dc.redeemed_at
),

trended as (
    select
        metric_date,
        redemption_rate_pct,
        redemptions,
        total_orders,
        total_discount,
        avg(redemption_rate_pct) over (order by metric_date rows between 6 preceding and current row) as rate_7d_ma,
        avg(redemption_rate_pct) over (order by metric_date rows between 27 preceding and current row) as rate_28d_ma
    from combined
)

select * from trended
