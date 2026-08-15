-- source extract for int_social_engagement_summary (PII columns excluded by the MDL projection)
select platform, total_posts, avg_engagement_rate, total_impressions, total_reach, total_likes, total_shares, total_comments, total_clicks, total_engagements, avg_click_through_rate, first_post_date, last_post_date
from main_marts.int_social_engagement_summary
