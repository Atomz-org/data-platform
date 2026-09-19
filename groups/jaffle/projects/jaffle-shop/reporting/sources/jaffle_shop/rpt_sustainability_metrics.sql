-- source extract for rpt_sustainability_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    waste_month,
    total_waste_cost,
    waste_cost_mom_pct
from main_marts.rpt_sustainability_metrics
