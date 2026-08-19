-- source extract for int_email_unsubscribe_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    unsubscribe_rate_pct,
    open_rate_pct
from main_marts.int_email_unsubscribe_analysis
