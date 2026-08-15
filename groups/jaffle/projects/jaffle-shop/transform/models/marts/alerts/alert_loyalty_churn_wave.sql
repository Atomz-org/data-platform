with

monthly_loyalty as (
    select
        {{ sf_date_trunc('month', "transacted_at") }} as txn_month,
        count(distinct loyalty_member_id) as active_members
    from {{ ref('fct_loyalty_transactions') }}
    group by 1
),

compared as (
    select
        txn_month,
        active_members,
        lag(active_members) over (order by txn_month) as prior_month_members,
        round(((active_members - lag(active_members) over (order by txn_month))) * 100.0
            / nullif(lag(active_members) over (order by txn_month), 0), 2) as member_change_pct
    from monthly_loyalty
),

alerts as (
    select
        txn_month,
        active_members,
        prior_month_members,
        member_change_pct,
        'loyalty_churn_wave' as alert_type,
        case when member_change_pct < -20 then 'critical' else 'warning' end as severity
    from compared
    where member_change_pct < -10
)

select * from alerts
