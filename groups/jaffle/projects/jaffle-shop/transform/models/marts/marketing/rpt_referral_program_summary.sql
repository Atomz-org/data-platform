with

referral_chain as (

    select * from {{ ref('int_referral_chain') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Get first order from referred customers to measure value
referee_first_orders as (

    select
        customer_id as referee_customer_id,
        min(ordered_at) as first_order_date,
        count(order_id) as total_orders,
        sum(order_total) as total_revenue

    from orders
    group by 1

),

-- Referral program overall metrics
referral_metrics as (

    select
        count(referral_id) as total_referrals,
        sum(case when referral_status = 'converted' then 1 else 0 end) as converted_referrals,
        sum(case when referral_status = 'pending' then 1 else 0 end) as pending_referrals,
        sum(case when referral_status = 'expired' then 1 else 0 end) as expired_referrals,
        count(distinct referrer_customer_id) as unique_referrers,
        count(distinct referee_customer_id) as unique_referees,
        sum(case when referral_status = 'converted' then reward_amount else 0 end) as total_rewards_paid,
        case
            when count(referral_id) > 0
            then sum(case when referral_status = 'converted' then 1 else 0 end) * 1.0 / count(referral_id)
            else 0
        end as overall_conversion_rate

    from referral_chain

),

-- Per-referrer summary with referee value
referrer_summary as (

    select
        referral_chain.referrer_customer_id,
        referral_chain.referrer_name,
        referral_chain.total_referrals_made,
        referral_chain.successful_referrals,
        referral_chain.referrer_total_rewards,
        referral_chain.referral_conversion_rate,
        sum(coalesce(referee_first_orders.total_revenue, 0)) as referee_total_revenue,
        sum(coalesce(referee_first_orders.total_orders, 0)) as referee_total_orders

    from referral_chain

    left join referee_first_orders
        on referral_chain.referee_customer_id = referee_first_orders.referee_customer_id

    where referral_chain.referral_status = 'converted'

    group by 1, 2, 3, 4, 5, 6

),

-- Top referrers with ROI
final as (

    select
        referrer_customer_id,
        referrer_name,
        total_referrals_made,
        successful_referrals,
        referrer_total_rewards,
        referral_conversion_rate,
        referee_total_revenue,
        referee_total_orders,
        case
            when referrer_total_rewards > 0
            then (referee_total_revenue - referrer_total_rewards) / referrer_total_rewards
            else null
        end as referrer_roi,
        row_number() over (order by referee_total_revenue desc) as referrer_rank

    from referrer_summary

)

select * from final
