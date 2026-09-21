-- source extract for int_campaign_by_store_performance (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    location_id,
    redemption_count,
    total_order_revenue
from main_marts.int_campaign_by_store_performance
