with

coupon_stats as (
    select
        coupon_id,
        count(*) as redemption_count,
        sum(discount_applied) as total_discount
    from {{ ref('fct_coupon_redemptions') }}
    group by 1
),

ranked as (
    select
        coupon_id,
        redemption_count,
        total_discount,
        round(total_discount * 1.0 / nullif(redemption_count, 0), 2) as avg_discount,
        rank() over (order by redemption_count desc) as redemption_rank,
        ntile(4) over (order by redemption_count desc) as redemption_quartile
    from coupon_stats
)

select * from ranked
