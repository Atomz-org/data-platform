-- source extract for mkt_brand_awareness_proxy (PII columns excluded by the MDL projection)
select platform, summary_month, total_engagement, total_impressions, post_count, engagement_growth_pct, impressions_growth_pct, engagement_rate_pct
from main_marts.mkt_brand_awareness_proxy
