with

monthly_coupons as (
    select
        {{ sf_date_trunc('month', "redeemed_at") }} as redemption_month,
        count(*) as redemptions,
        sum(discount_applied) as total_discount,
        count(distinct coupon_id) as unique_coupons
    from {{ ref('fct_coupon_redemptions') }}
    group by 1
),

compared as (
    select
        redemption_month,
        redemptions as current_redemptions,
        lag(redemptions) over (order by redemption_month) as prior_month_redemptions,
        total_discount as current_discount,
        lag(total_discount) over (order by redemption_month) as prior_month_discount,
        round(((redemptions - lag(redemptions) over (order by redemption_month))) * 100.0
            / nullif(lag(redemptions) over (order by redemption_month), 0), 2) as redemptions_mom_pct,
        round(((total_discount - lag(total_discount) over (order by redemption_month))) * 100.0
            / nullif(lag(total_discount) over (order by redemption_month), 0), 2) as discount_mom_pct
    from monthly_coupons
)

select * from compared
