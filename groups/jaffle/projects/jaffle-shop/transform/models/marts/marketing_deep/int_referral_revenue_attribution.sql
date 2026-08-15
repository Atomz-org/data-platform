with

referrals as (

    select * from {{ ref('stg_referrals') }}

),

orders as (

    select
        customer_id,
        order_id,
        order_total,
        ordered_at
    from {{ ref('stg_orders') }}

),

referee_orders as (

    select
        r.referral_id,
        r.referrer_customer_id,
        r.referee_customer_id,
        r.referral_status,
        r.reward_amount,
        r.referred_at,
        r.converted_at,
        o.order_id,
        o.order_total,
        o.ordered_at
    from referrals as r
    inner join orders as o
        on r.referee_customer_id = o.customer_id
    where r.referral_status = 'converted'

),

referrer_summary as (

    select
        referrer_customer_id,
        count(distinct referee_customer_id) as total_referees,
        count(distinct referral_id) as total_referrals,
        count(distinct order_id) as referee_order_count,
        sum(order_total) as total_attributed_revenue,
        sum(reward_amount) as total_rewards_paid,
        sum(order_total) - sum(reward_amount) as net_referral_revenue
    from referee_orders
    group by 1

)

select * from referrer_summary
