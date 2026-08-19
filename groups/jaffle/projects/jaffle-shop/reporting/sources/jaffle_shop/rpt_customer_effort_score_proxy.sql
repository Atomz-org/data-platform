-- source extract for rpt_customer_effort_score_proxy (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    effort_month,
    refund_rate_pct,
    effort_tier
from main_marts.rpt_customer_effort_score_proxy
