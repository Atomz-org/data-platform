-- source extract for int_store_marketing_spend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    store_id,
    spend_month,
    monthly_marketing_spend,
    top_spend_channel
from main_marts.int_store_marketing_spend
