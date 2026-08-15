with

marketing as (

    select * from {{ ref('int_marketing_spend_daily') }}

),

loyalty_txns as (

    select * from {{ ref('fct_loyalty_transactions') }}

),

coupons as (

    select * from {{ ref('fct_coupon_redemptions') }}

),

monthly_spend as (

    select
        {{ dbt.date_trunc('month', 'spend_date') }} as month_start,
        sum(channel_spend) as total_marketing_spend,
        count(distinct spend_channel) as channels_used,
        sum(campaigns_active) as total_campaign_days

    from marketing
    group by 1

),

monthly_loyalty as (

    select
        {{ dbt.date_trunc('month', 'transacted_at') }} as month_start,
        count(distinct case when transaction_type = 'earn' then loyalty_member_id end) as active_loyalty_members,
        count(case when transaction_type = 'earn' then 1 end) as loyalty_earn_events,
        count(case when transaction_type = 'redeem' then 1 end) as loyalty_redeem_events,
        sum(case when transaction_type = 'earn' then points else 0 end) as points_earned,
        sum(case when transaction_type = 'redeem' then abs(points) else 0 end) as points_redeemed

    from loyalty_txns
    group by 1

),

monthly_coupons as (

    select
        {{ dbt.date_trunc('month', 'redeemed_at') }} as month_start,
        count(redemption_id) as coupon_redemptions,
        sum(discount_applied) as total_discount_given,
        count(distinct customer_id) as customers_using_coupons

    from coupons
    group by 1

),

final as (

    select
        ms.month_start,
        ms.total_marketing_spend,
        ms.channels_used,
        ms.total_campaign_days,
        coalesce(ml.active_loyalty_members, 0) as active_loyalty_members,
        coalesce(ml.loyalty_earn_events, 0) as loyalty_earn_events,
        coalesce(ml.loyalty_redeem_events, 0) as loyalty_redeem_events,
        coalesce(ml.points_earned, 0) as points_earned,
        coalesce(ml.points_redeemed, 0) as points_redeemed,
        coalesce(mc.coupon_redemptions, 0) as coupon_redemptions,
        coalesce(mc.total_discount_given, 0) as total_discount_given,
        coalesce(mc.customers_using_coupons, 0) as customers_using_coupons

    from monthly_spend as ms

    left join monthly_loyalty as ml
        on ms.month_start = ml.month_start

    left join monthly_coupons as mc
        on ms.month_start = mc.month_start

)

select * from final
