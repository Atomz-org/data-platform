with

referrals as (

    select * from {{ ref('stg_referrals') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

-- Build referrer-referee relationships with customer details
referral_relationships as (

    select
        referrals.referral_id,
        referrals.referral_code,
        referrals.referral_status,
        referrals.referred_at,
        referrals.converted_at,
        referrals.reward_amount,
        referrals.campaign_id,

        -- Referrer info
        referrals.referrer_customer_id,
        referrer.customer_name as referrer_name,

        -- Referee info
        referrals.referee_customer_id,
        referee.customer_name as referee_name

    from referrals

    inner join customers as referrer
        on referrals.referrer_customer_id = referrer.customer_id

    inner join customers as referee
        on referrals.referee_customer_id = referee.customer_id

),

-- Count how many successful referrals each customer has made
referrer_stats as (

    select
        referrer_customer_id,
        count(referral_id) as total_referrals_made,
        sum(case when referral_status = 'converted' then 1 else 0 end) as successful_referrals,
        sum(case when referral_status = 'pending' then 1 else 0 end) as pending_referrals,
        sum(case when referral_status = 'expired' then 1 else 0 end) as expired_referrals,
        sum(case when referral_status = 'converted' then reward_amount else 0 end) as total_rewards_earned,
        min(referred_at) as first_referral_date,
        max(referred_at) as last_referral_date,
        case
            when count(referral_id) > 0
            then sum(case when referral_status = 'converted' then 1 else 0 end) * 1.0 / count(referral_id)
            else 0
        end as referral_conversion_rate

    from referral_relationships
    group by 1

),

-- Final: join referral relationships with referrer stats
referral_chain as (

    select
        referral_relationships.*,
        referrer_stats.total_referrals_made,
        referrer_stats.successful_referrals,
        referrer_stats.total_rewards_earned as referrer_total_rewards,
        referrer_stats.referral_conversion_rate

    from referral_relationships

    left join referrer_stats
        on referral_relationships.referrer_customer_id = referrer_stats.referrer_customer_id

)

select * from referral_chain
