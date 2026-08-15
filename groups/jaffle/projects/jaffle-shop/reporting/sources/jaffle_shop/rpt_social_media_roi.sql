-- source extract for rpt_social_media_roi (PII columns excluded by the MDL projection)
select platform, total_posts, total_impressions, total_reach, total_likes, total_shares, total_comments, total_clicks, total_engagements, avg_engagement_rate, avg_click_through_rate, social_campaign_spend, social_campaign_revenue, social_campaign_orders, social_roi, cost_per_engagement, revenue_per_click
from main_marts.rpt_social_media_roi
