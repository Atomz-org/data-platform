with final as (
    select
        month_start,
        total_marketing_spend,
        total_campaign_days,
        round(total_marketing_spend * 1.0 / nullif(total_marketing_spend, 0), 2) as avg_roi,
        round(total_marketing_spend * 1.0 / nullif(total_campaign_days, 0), 2) as avg_spend_per_campaign
    from {{ ref('met_monthly_marketing_metrics') }}
)
select * from final
