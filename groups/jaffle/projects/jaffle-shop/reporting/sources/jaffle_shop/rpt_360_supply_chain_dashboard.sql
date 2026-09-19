-- source extract for rpt_360_supply_chain_dashboard (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    total_suppliers,
    avg_reliability_score,
    total_inventory_value
from main_marts.rpt_360_supply_chain_dashboard
