-- source extract for int_social_engagement_summary (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    platform,
    total_posts,
    avg_engagement_rate,
    total_impressions
from main_marts.int_social_engagement_summary
