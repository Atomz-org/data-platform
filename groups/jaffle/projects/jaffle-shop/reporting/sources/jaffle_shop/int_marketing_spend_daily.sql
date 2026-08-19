-- source extract for int_marketing_spend_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    spend_date,
    spend_channel,
    channel_spend,
    total_daily_spend,
    channel_spend_7d_avg
from main_marts.int_marketing_spend_daily
