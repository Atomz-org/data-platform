-- source extract for rpt_supply_demand_alignment (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    supply_demand_ratio,
    alignment_status
from main_marts.rpt_supply_demand_alignment
