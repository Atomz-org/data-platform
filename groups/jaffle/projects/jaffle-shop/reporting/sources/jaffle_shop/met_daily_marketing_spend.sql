-- source extract for met_daily_marketing_spend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    spend_date,
    spend_channel,
    total_spend_7d_avg
from main_marts.met_daily_marketing_spend
