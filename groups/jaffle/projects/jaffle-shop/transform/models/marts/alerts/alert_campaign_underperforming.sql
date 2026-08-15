with

campaign_performance as (
    select
        campaign_id,
        campaign_name,
        total_spend,
        budget,
        budget_utilization,
        active_spend_days
    from {{ ref('fct_campaigns') }}
    where total_spend > 0
),

alerts as (
    select
        cp.campaign_id,
        cp.campaign_name,
        cp.total_spend,
        cp.budget,
        cp.budget_utilization,
        cp.active_spend_days,
        'campaign_underperforming' as alert_type,
        case when cp.budget_utilization > 1.5 then 'critical' else 'warning' end as severity
    from campaign_performance as cp
    where cp.budget_utilization > 1.0 or cp.active_spend_days < 3
)

select * from alerts
