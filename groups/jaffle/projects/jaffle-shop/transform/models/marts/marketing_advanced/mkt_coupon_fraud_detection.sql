with

redemptions as (

    select
        coupon_id,
        customer_id,
        order_id,
        discount_applied,
        redeemed_at,
        {{ dbt.date_trunc('day', 'redeemed_at') }} as redemption_date
    from {{ ref('fct_coupon_redemptions') }}

),

coupon_stats as (

    select
        coupon_id,
        count(*) as total_redemptions,
        count(distinct customer_id) as unique_customers,
        sum(discount_applied) as total_discount_given,
        max(discount_applied) as max_single_discount,
        avg(discount_applied) as avg_discount
    from redemptions
    group by 1

),

customer_coupon_freq as (

    select
        customer_id,
        coupon_id,
        count(*) as uses_by_customer,
        sum(discount_applied) as total_discount_by_customer
    from redemptions
    group by 1, 2

),

daily_spikes as (

    select
        coupon_id,
        redemption_date,
        count(*) as daily_redemptions,
        avg(count(*)) over (partition by coupon_id) as avg_daily_redemptions
    from redemptions
    group by 1, 2

),

anomalies as (

    select
        coupon_id,
        count(case when daily_redemptions > avg_daily_redemptions * 3 then 1 end) as spike_days
    from daily_spikes
    group by 1

),

final as (

    select
        cs.coupon_id,
        cs.total_redemptions,
        cs.unique_customers,
        cs.total_discount_given,
        cs.avg_discount,
        coalesce(a.spike_days, 0) as usage_spike_days,
        max(ccf.uses_by_customer) as max_uses_by_single_customer,
        case
            when max(ccf.uses_by_customer) > 5 then 'potential_abuse'
            when coalesce(a.spike_days, 0) > 2 then 'suspicious_pattern'
            when cs.total_redemptions > 100 and cs.unique_customers < cs.total_redemptions * 0.3
            then 'low_customer_diversity'
            else 'normal'
        end as fraud_risk_flag
    from coupon_stats as cs
    left join anomalies as a on cs.coupon_id = a.coupon_id
    left join customer_coupon_freq as ccf on cs.coupon_id = ccf.coupon_id
    group by 1, 2, 3, 4, 5, 6

)

select * from final
