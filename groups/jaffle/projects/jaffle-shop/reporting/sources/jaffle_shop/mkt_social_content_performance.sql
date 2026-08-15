-- source extract for mkt_social_content_performance (PII columns excluded by the MDL projection)
select platform, post_type, post_count, total_engagement, avg_engagement_per_post, total_impressions, engagement_rate_pct, avg_likes, avg_shares, avg_comment_count, engagement_rank
from main_marts.mkt_social_content_performance
