with

referral_chain as (

    select * from {{ ref('int_referral_chain') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

-- Check which referred customers actually made purchases
referee_purchases as (

    select
        orders.customer_id as referee_customer_id,
        count(distinct orders.order_id) as referee_order_count,
        sum(orders.order_total) as referee_total_spend,
        min(orders.ordered_at) as referee_first_order_date

    from orders
    group by 1

),

-- Join referrals with purchase data
referral_with_purchases as (

    select
        referral_chain.referral_id,
        referral_chain.referral_code,
        referral_chain.referral_status,
        referral_chain.referred_at,
        referral_chain.converted_at,
        referral_chain.reward_amount,
        referral_chain.referrer_customer_id,
        referral_chain.referrer_name,
        referral_chain.referee_customer_id,
        referral_chain.referee_name,
        coalesce(referee_purchases.referee_order_count, 0) as referee_order_count,
        coalesce(referee_purchases.referee_total_spend, 0) as referee_total_spend,
        referee_purchases.referee_first_order_date,
        -- Did the referee actually purchase?
        case
            when referee_purchases.referee_order_count > 0 then true
            else false
        end as referee_made_purchase

    from referral_chain

    left join referee_purchases
        on referral_chain.referee_customer_id = referee_purchases.referee_customer_id

),

-- Overall conversion rate summary
conversion_summary as (

    select
        count(referral_id) as total_referrals,
        sum(case when referral_status = 'converted' then 1 else 0 end) as status_converted,
        sum(case when referee_made_purchase then 1 else 0 end) as referees_who_purchased,
        sum(case
            when referral_status = 'converted' and referee_made_purchase
            then 1 else 0
        end) as converted_and_purchased,
        -- Conversion rate: referrals that converted to status
        case
            when count(referral_id) > 0
            then sum(case when referral_status = 'converted' then 1 else 0 end) * 1.0 / count(referral_id)
            else 0
        end as status_conversion_rate,
        -- Purchase rate: converted referees who made purchases
        case
            when sum(case when referral_status = 'converted' then 1 else 0 end) > 0
            then sum(case when referral_status = 'converted' and referee_made_purchase then 1 else 0 end) * 1.0
                / sum(case when referral_status = 'converted' then 1 else 0 end)
            else 0
        end as purchase_conversion_rate,
        sum(case when referee_made_purchase then referee_total_spend else 0 end) as total_referee_revenue,
        sum(reward_amount) as total_rewards_paid,
        -- ROI of referral program
        case
            when sum(reward_amount) > 0
            then (sum(case when referee_made_purchase then referee_total_spend else 0 end) - sum(reward_amount))
                / sum(reward_amount)
            else null
        end as referral_program_roi

    from referral_with_purchases

)

select * from conversion_summary
