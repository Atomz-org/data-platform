with

points_balance as (

    select * from {{ ref('int_loyalty_points_balance') }}

),

loyalty_transactions as (

    select * from {{ ref('fct_loyalty_transactions') }}

),

-- Calculate recent activity metrics per member
recent_activity as (

    select
        loyalty_member_id,
        max(transacted_at) as last_transaction_date,
        -- Days since last transaction
        {{ dbt.datediff('max(transacted_at)', 'current_date', 'day') }} as days_since_last_transaction,
        -- Points earned in the last 90 days
        sum(case
            when transaction_type = 'earn'
                and transacted_at >= {{ dbt.dateadd('day', -90, 'current_date') }}
            then points else 0
        end) as points_earned_last_90d,
        -- Points earned in the prior 90 days (91-180 days ago)
        sum(case
            when transaction_type = 'earn'
                and transacted_at >= {{ dbt.dateadd('day', -180, 'current_date') }}
                and transacted_at < {{ dbt.dateadd('day', -90, 'current_date') }}
            then points else 0
        end) as points_earned_prior_90d,
        -- Transaction count last 90 days
        count(case
            when transacted_at >= {{ dbt.dateadd('day', -90, 'current_date') }}
            then loyalty_transaction_id
        end) as transactions_last_90d

    from loyalty_transactions
    group by 1

),

-- Combine with balance and compute churn risk
churn_risk as (

    select
        points_balance.loyalty_member_id,
        points_balance.current_points_balance,
        points_balance.total_points_earned,
        points_balance.total_points_redeemed,
        points_balance.total_transactions,
        points_balance.first_transaction_date,
        recent_activity.last_transaction_date,
        recent_activity.days_since_last_transaction,
        recent_activity.points_earned_last_90d,
        recent_activity.points_earned_prior_90d,
        recent_activity.transactions_last_90d,
        -- Declining activity flag
        case
            when recent_activity.points_earned_last_90d < recent_activity.points_earned_prior_90d
            then true
            else false
        end as is_declining_activity,
        -- Churn risk level
        case
            when recent_activity.days_since_last_transaction >= 120 then 'critical'
            when recent_activity.days_since_last_transaction >= 60
                and recent_activity.points_earned_last_90d < recent_activity.points_earned_prior_90d
            then 'high'
            when recent_activity.days_since_last_transaction >= 60 then 'medium'
            when recent_activity.points_earned_last_90d < recent_activity.points_earned_prior_90d
            then 'low'
            else 'healthy'
        end as churn_risk_level

    from points_balance

    inner join recent_activity
        on points_balance.loyalty_member_id = recent_activity.loyalty_member_id

)

select * from churn_risk
