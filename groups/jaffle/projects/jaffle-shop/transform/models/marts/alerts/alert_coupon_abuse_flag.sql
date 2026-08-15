with

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

customer_coupon_usage as (
    select
        cr.customer_id,
        count(*) as total_redemptions,
        count(distinct cr.coupon_id) as unique_coupons,
        sum(cr.discount_applied) as total_discount,
        avg(cr.discount_applied) as avg_discount,
        count(*) * 1.0 / nullif(count(distinct {{ sf_date_trunc('month', "cr.redeemed_at") }}), 0) as redemptions_per_month
    from cr
    group by 1
),

thresholds as (
    select
        avg(total_redemptions) + 3 * coalesce(nullif(stddev(total_redemptions), 0), 1) as redemption_threshold,
        avg(total_discount) + 3 * coalesce(nullif(stddev(total_discount), 0), 1) as discount_threshold
    from customer_coupon_usage
),

alerts as (
    select
        cu.customer_id,
        cu.total_redemptions,
        cu.total_discount,
        cu.redemptions_per_month,
        'coupon_abuse_flag' as alert_type,
        case
            when cu.total_redemptions > t.redemption_threshold
                and cu.total_discount > t.discount_threshold then 'critical'
            when cu.total_redemptions > t.redemption_threshold
                or cu.total_discount > t.discount_threshold then 'warning'
            else 'info'
        end as severity
    from customer_coupon_usage as cu
    cross join thresholds as t
    where cu.total_redemptions > t.redemption_threshold
       or cu.total_discount > t.discount_threshold
)

select * from alerts
