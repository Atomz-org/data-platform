-- source extract for rpt_omnichannel_customer (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    stores_visited,
    store_engagement_tier
from main_marts.rpt_omnichannel_customer
