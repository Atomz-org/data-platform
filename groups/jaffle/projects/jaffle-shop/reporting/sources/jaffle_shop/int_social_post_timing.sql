-- source extract for int_social_post_timing (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    platform,
    day_name,
    engagement_rate_pct
from main_marts.int_social_post_timing
