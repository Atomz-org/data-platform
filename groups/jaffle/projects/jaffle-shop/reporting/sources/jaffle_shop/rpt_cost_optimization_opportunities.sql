-- source extract for rpt_cost_optimization_opportunities (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    optimization_area,
    metric_value
from main_marts.rpt_cost_optimization_opportunities
