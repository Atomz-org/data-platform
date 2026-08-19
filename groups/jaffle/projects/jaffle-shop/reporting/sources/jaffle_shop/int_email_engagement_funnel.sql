-- source extract for int_email_engagement_funnel (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    open_rate,
    click_through_rate,
    unsubscribe_rate
from main_marts.int_email_engagement_funnel
