with

campaigns as (
    select * from {{ ref('rpt_campaign_effectiveness') }}
)

select
    campaign_id,
    campaign_name,
    campaign_channel,
    total_spend,
    attributed_revenue as total_revenue_attributed,
    round(roi_ratio * 100, 2) as roi_pct,
    attributed_orders as total_conversions,
    cost_per_order as cost_per_conversion,
    effectiveness_tier,
    case
        when roi_ratio >= 2 then 'high_performer'
        when roi_ratio >= 1 then 'profitable'
        when roi_ratio >= 0 then 'break_even'
        else 'underperforming'
    end as campaign_tier
from campaigns
