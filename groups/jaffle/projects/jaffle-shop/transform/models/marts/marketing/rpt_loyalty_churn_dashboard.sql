with

churn_risk as (

    select * from {{ ref('int_loyalty_churn_risk') }}

),

loyalty_members as (

    select * from {{ ref('dim_loyalty_members') }}

),

-- Join churn risk with member details
member_churn as (

    select
        churn_risk.loyalty_member_id,
        loyalty_members.customer_id,
        loyalty_members.membership_status,
        loyalty_members.current_tier_name,
        loyalty_members.enrolled_at,
        loyalty_members.last_activity_at,
        loyalty_members.lifetime_points,
        loyalty_members.total_points_earned,
        loyalty_members.total_points_redeemed,
        churn_risk.current_points_balance,
        churn_risk.last_transaction_date,
        churn_risk.days_since_last_transaction,
        churn_risk.points_earned_last_90d,
        churn_risk.points_earned_prior_90d,
        churn_risk.transactions_last_90d,
        churn_risk.is_declining_activity,
        churn_risk.churn_risk_level

    from churn_risk

    inner join loyalty_members
        on churn_risk.loyalty_member_id = loyalty_members.loyalty_member_id

    where loyalty_members.is_active_member

),

-- Summary by risk level
risk_summary as (

    select
        churn_risk_level,
        count(loyalty_member_id) as member_count,
        avg(days_since_last_transaction) as avg_days_inactive,
        avg(lifetime_points) as avg_lifetime_points,
        sum(current_points_balance) as total_points_at_risk,
        avg(points_earned_last_90d) as avg_recent_points,
        avg(points_earned_prior_90d) as avg_prior_points

    from member_churn
    group by 1

)

-- Return member-level detail for dashboard
select
    member_churn.*,
    risk_summary.member_count as risk_level_member_count,
    risk_summary.total_points_at_risk as risk_level_total_points_at_risk

from member_churn

left join risk_summary
    on member_churn.churn_risk_level = risk_summary.churn_risk_level

order by
    case member_churn.churn_risk_level
        when 'critical' then 1
        when 'high' then 2
        when 'medium' then 3
        when 'low' then 4
        else 5
    end,
    member_churn.days_since_last_transaction desc
