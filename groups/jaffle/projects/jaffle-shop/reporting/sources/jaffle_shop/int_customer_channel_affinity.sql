-- source extract for int_customer_channel_affinity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    channel,
    channel_rank,
    channel_pct
from main_marts.int_customer_channel_affinity
