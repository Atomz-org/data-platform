-- source extract for rpt_operational_cost_per_order (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    order_month,
    cost_per_order
from main_marts.rpt_operational_cost_per_order
