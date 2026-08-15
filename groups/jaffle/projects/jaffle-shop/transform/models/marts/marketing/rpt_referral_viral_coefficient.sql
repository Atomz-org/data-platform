with

rc2 as (
    select * from {{ ref('int_referral_chain') }}
),

referral_conversion as (

    select * from {{ ref('int_referral_conversion_rate') }}

),

referral_chain as (

    select * from {{ ref('int_referral_chain') }}

),

-- Count unique referrers and total customers involved
referrer_stats as (

    select
        count(distinct referrer_customer_id) as total_referrers,
        count(distinct referee_customer_id) as total_referees,
        count(referral_id) as total_referrals,
        sum(case when referral_status = 'converted' then 1 else 0 end) as converted_referrals,
        -- Average referrals made per referrer
        case
            when count(distinct referrer_customer_id) > 0
            then count(referral_id) * 1.0 / count(distinct referrer_customer_id)
            else 0
        end as avg_referrals_per_referrer,
        -- Average successful referrals per referrer
        case
            when count(distinct referrer_customer_id) > 0
            then sum(case when referral_status = 'converted' then 1 else 0 end) * 1.0
                / count(distinct referrer_customer_id)
            else 0
        end as avg_successful_referrals_per_referrer,
        -- Viral coefficient = avg invites sent * conversion rate
        -- K = i * c where i = invites per user, c = conversion rate
        case
            when count(distinct referrer_customer_id) > 0
                and count(referral_id) > 0
            then (count(referral_id) * 1.0 / count(distinct referrer_customer_id))
                * (sum(case when referral_status = 'converted' then 1 else 0 end) * 1.0 / count(referral_id))
            else 0
        end as viral_coefficient

    from referral_chain

),

-- Distribution of referrals per referrer
referral_distribution as (

    select
        referrer_customer_id,
        total_referrals_made,
        successful_referrals,
        referral_conversion_rate

    from referral_chain
    -- Deduplicate to one row per referrer
    where referral_id = (
        select min(rc2.referral_id)
        from rc2
        where rc2.referrer_customer_id = referral_chain.referrer_customer_id
    )

),

distribution_summary as (

    select
        avg(total_referrals_made) as avg_referrals_made,
        avg(successful_referrals) as avg_successful_referrals,
        max(total_referrals_made) as max_referrals_by_single_user,
        avg(referral_conversion_rate) as avg_referrer_conversion_rate,
        -- Referrers with 3+ successful referrals (super referrers)
        sum(case when successful_referrals >= 3 then 1 else 0 end) as super_referrer_count,
        count(*) as total_unique_referrers

    from referral_distribution

),

-- Final: combine all metrics
final as (

    select
        referrer_stats.total_referrers,
        referrer_stats.total_referees,
        referrer_stats.total_referrals,
        referrer_stats.converted_referrals,
        referrer_stats.avg_referrals_per_referrer,
        referrer_stats.avg_successful_referrals_per_referrer,
        referrer_stats.viral_coefficient,
        case
            when referrer_stats.viral_coefficient >= 1 then 'viral_growth'
            when referrer_stats.viral_coefficient >= 0.5 then 'strong_referral'
            when referrer_stats.viral_coefficient >= 0.2 then 'moderate_referral'
            else 'low_referral'
        end as virality_tier,
        referral_conversion.status_conversion_rate,
        referral_conversion.purchase_conversion_rate,
        referral_conversion.total_referee_revenue,
        referral_conversion.total_rewards_paid,
        referral_conversion.referral_program_roi,
        distribution_summary.max_referrals_by_single_user,
        distribution_summary.super_referrer_count,
        distribution_summary.avg_referrer_conversion_rate

    from referrer_stats

    cross join referral_conversion

    cross join distribution_summary

)

select * from final
