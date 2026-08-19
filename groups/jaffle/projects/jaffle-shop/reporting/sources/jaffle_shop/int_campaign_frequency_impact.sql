-- source extract for int_campaign_frequency_impact (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    send_month,
    send_frequency_tier,
    avg_open_rate,
    avg_unsubscribe_rate
from main_marts.int_campaign_frequency_impact
