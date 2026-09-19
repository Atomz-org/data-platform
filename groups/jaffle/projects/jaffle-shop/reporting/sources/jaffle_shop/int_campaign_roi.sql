-- source extract for int_campaign_roi (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    campaign_id,
    total_spend,
    attributed_revenue,
    roi_ratio,
    cost_per_order
from main_marts.int_campaign_roi
