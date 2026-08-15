with

coupons as (

    select * from {{ ref('stg_coupons') }}

),

coupon_redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

redemption_stats as (

    select
        coupon_id,
        count(redemption_id) as total_redemptions,
        count(distinct customer_id) as unique_customers,
        sum(discount_applied) as total_discount_given,
        avg(discount_applied) as avg_discount_per_redemption,
        min(redeemed_at) as first_redeemed_at,
        max(redeemed_at) as last_redeemed_at

    from coupon_redemptions
    group by 1

),

coupon_performance as (

    select
        coupons.coupon_id,
        coupons.coupon_code,
        coupons.discount_type,
        coupons.discount_amount,
        coupons.discount_percent,
        coupons.coupon_status,
        coupons.max_redemptions,
        coupons.valid_from,
        coupons.valid_until,
        coupons.campaign_id,
        coalesce(redemption_stats.total_redemptions, 0) as total_redemptions,
        coalesce(redemption_stats.unique_customers, 0) as unique_customers,
        coalesce(redemption_stats.total_discount_given, 0) as total_discount_given,
        redemption_stats.avg_discount_per_redemption,
        case
            when coupons.max_redemptions is not null and coupons.max_redemptions > 0
            then coalesce(redemption_stats.total_redemptions, 0) * 1.0 / coupons.max_redemptions
            else null
        end as redemption_rate,
        redemption_stats.first_redeemed_at,
        redemption_stats.last_redeemed_at

    from coupons

    left join redemption_stats
        on coupons.coupon_id = redemption_stats.coupon_id

)

select * from coupon_performance
