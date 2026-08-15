with

campaign_roi as (
    select * from {{ ref('int_campaign_roi') }}
),

campaigns as (
    select * from {{ ref('dim_campaigns') }}
)

select
    cr.campaign_id,
    cr.campaign_name,
    cr.campaign_channel,
    cr.total_spend,
    cr.attributed_revenue,
    cr.roi_ratio,
    round(cr.roi_ratio * 100, 2) as roi_pct,
    case
        when cr.roi_ratio >= 2 then 'highly_effective'
        when cr.roi_ratio >= 1 then 'effective'
        when cr.roi_ratio >= 0 then 'break_even'
        else 'ineffective'
    end as effectiveness_tier
from campaign_roi as cr
