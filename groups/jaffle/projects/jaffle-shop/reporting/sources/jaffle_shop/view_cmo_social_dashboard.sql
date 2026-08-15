-- source extract for view_cmo_social_dashboard (PII columns excluded by the MDL projection)
select platform, total_posts, impressions, engagements, total_spend, attributed_revenue, engagement_rate_pct, social_roas, cost_per_engagement
from main_marts.view_cmo_social_dashboard
