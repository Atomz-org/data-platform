-- source extract for int_social_post_timing (PII columns excluded by the MDL projection)
select platform, day_name, engagement_rate_pct, post_type, day_of_week, post_count, avg_impressions, avg_reach, avg_likes, avg_shares, avg_clicks, total_engagements
from main_marts.int_social_post_timing
