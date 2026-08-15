with monthly as (
    select month_start, total_marketing_spend, total_campaign_days
    from {{ ref('met_monthly_marketing_metrics') }}
),
final as (
    select
        {{ sf_date_trunc('quarter', "month_start") }} as metric_quarter,
        sum(total_marketing_spend) as quarterly_spend,
        sum(total_campaign_days) as quarterly_campaigns,
        sum(total_marketing_spend) as quarterly_revenue,
        round(sum(total_marketing_spend) * 1.0 / nullif(sum(total_marketing_spend), 0), 2) as quarterly_roi
    from monthly
    group by 1
)
select * from final
