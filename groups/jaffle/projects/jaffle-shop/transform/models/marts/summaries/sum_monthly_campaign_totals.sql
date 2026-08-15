with final as (
    select
        month_start,
        total_marketing_spend,
        total_campaign_days,
        round(total_marketing_spend * 1.0 / nullif(total_marketing_spend, 0), 2) as overall_roi,
        lag(total_marketing_spend) over (order by month_start) as prior_month_spend
    from {{ ref('met_monthly_marketing_metrics') }}
)
select * from final
