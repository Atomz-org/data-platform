with

social_roi as (
    select * from {{ ref('rpt_social_media_roi') }}
)

select
    platform,
    total_posts,
    total_impressions as impressions,
    total_engagements as engagements,
    social_campaign_spend as total_spend,
    social_campaign_revenue as attributed_revenue,
    round(total_engagements * 100.0 / nullif(total_impressions, 0), 2) as engagement_rate_pct,
    round(social_campaign_revenue / nullif(social_campaign_spend, 0), 2) as social_roas,
    round(social_campaign_spend / nullif(total_engagements, 0), 2) as cost_per_engagement
from social_roi
