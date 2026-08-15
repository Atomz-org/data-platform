with

monthly_marketing as (
    select
        month_start,
        total_marketing_spend,
        total_campaign_days
    from {{ ref('met_monthly_marketing_metrics') }}
),

compared as (
    select
        month_start,
        total_marketing_spend as current_spend,
        lag(total_marketing_spend) over (order by month_start) as prior_month_spend,
        total_campaign_days as current_campaigns,
        lag(total_campaign_days) over (order by month_start) as prior_month_campaigns,
        round(((total_marketing_spend - lag(total_marketing_spend) over (order by month_start))) * 100.0
            / nullif(lag(total_marketing_spend) over (order by month_start), 0), 2) as spend_mom_pct,
        round(total_marketing_spend * 1.0 / nullif(total_campaign_days, 0), 2) as avg_spend_per_campaign
    from monthly_marketing
)

select * from compared
