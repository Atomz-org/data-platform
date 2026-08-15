with

o as (
    select * from {{ ref('stg_orders') }}
),

referrals as (

    select
        referrer_customer_id,
        referee_customer_id as customer_id,
        1 as referral_depth,
        referred_at as referral_date
    from {{ ref('int_referral_chain') }}

),

network_stats as (

    select
        referrer_customer_id,
        count(distinct customer_id) as total_referrals,
        max(referral_depth) as max_chain_depth,
        min(referral_date) as first_referral_date,
        max(referral_date) as last_referral_date
    from referrals
    group by 1

),

referred_value as (

    select
        r.referrer_customer_id,
        sum(o.order_total) as referred_customer_revenue
    from referrals as r
    inner join o
        on r.customer_id = o.customer_id
        and o.order_total = o.order_total
    group by 1

),

final as (

    select
        ns.referrer_customer_id,
        ns.total_referrals,
        ns.max_chain_depth,
        ns.first_referral_date,
        ns.last_referral_date,
        coalesce(rv.referred_customer_revenue, 0) as total_referred_revenue,
        case
            when ns.total_referrals > 0
            then coalesce(rv.referred_customer_revenue, 0) / ns.total_referrals
            else 0
        end as avg_revenue_per_referral,
        case
            when ns.total_referrals >= 10 then 'super_referrer'
            when ns.total_referrals >= 5 then 'active_referrer'
            when ns.total_referrals >= 1 then 'casual_referrer'
            else 'non_referrer'
        end as referrer_tier
    from network_stats as ns
    left join referred_value as rv on ns.referrer_customer_id = rv.referrer_customer_id

)

select * from final
