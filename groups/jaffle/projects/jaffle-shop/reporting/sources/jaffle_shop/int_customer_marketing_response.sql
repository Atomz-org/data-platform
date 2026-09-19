-- source extract for int_customer_marketing_response (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    campaign_response_rate_pct,
    marketing_engagement_level
from main_marts.int_customer_marketing_response
