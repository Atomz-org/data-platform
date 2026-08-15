with

members as (

    select
        customer_id,
        loyalty_member_id,
        current_tier_name,
        enrolled_at
    from {{ ref('dim_loyalty_members') }}

),

transactions as (

    select
        customer_id,
        count(*) as total_txns,
        sum(case when transaction_type = 'redeem' then 1 else 0 end) as redemption_count,
        max(transacted_at) as last_txn_date,
        {{ dbt.datediff('max(transacted_at)', 'current_date', 'day') }} as days_since_last_txn
    from {{ ref('fct_loyalty_transactions') }}
    group by 1

),

balances as (

    select loyalty_member_id, current_points_balance as points_balance
    from {{ ref('int_loyalty_points_balance') }}

),

final as (

    select
        m.customer_id,
        m.loyalty_member_id,
        m.current_tier_name,
        m.enrolled_at,
        coalesce(t.total_txns, 0) as total_transactions,
        coalesce(t.redemption_count, 0) as redemption_count,
        coalesce(t.days_since_last_txn, 999) as days_since_last_txn,
        coalesce(b.points_balance, 0) as current_points,
        -- Engagement score: 0-100
        {{ sf_least(["100", "((least(coalesce(t.total_txns, 0), 50) * 1.0) + (case when coalesce(t.days_since_last_txn, 999) < 30 then 30 when coalesce(t.days_since_last_txn, 999) < 90 then 15 else 0 end) + (least(coalesce(t.redemption_count, 0), 10) * 2.0))"]) }} as engagement_score,
        case
            when {{ sf_least(["100", "((least(coalesce(t.total_txns, 0), 50) * 1.0) + (case when coalesce(t.days_since_last_txn, 999) < 30 then 30 when coalesce(t.days_since_last_txn, 999) < 90 then 15 else 0 end) + (least(coalesce(t.redemption_count, 0), 10) * 2.0))"]) }} >= 70 then 'highly_engaged'
            when {{ sf_least(["100", "((least(coalesce(t.total_txns, 0), 50) * 1.0) + (case when coalesce(t.days_since_last_txn, 999) < 30 then 30 when coalesce(t.days_since_last_txn, 999) < 90 then 15 else 0 end) + (least(coalesce(t.redemption_count, 0), 10) * 2.0))"]) }} >= 40 then 'moderately_engaged'
            else 'low_engagement'
        end as engagement_tier
    from members as m
    left join transactions as t on m.customer_id = t.customer_id
    left join balances as b on m.loyalty_member_id = b.loyalty_member_id

)

select * from final
