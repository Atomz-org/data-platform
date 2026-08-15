-- source extract for rpt_cost_optimization_opportunities (PII columns excluded by the MDL projection)
select location_id, optimization_area, metric_value, flag_month, detail
from main_marts.rpt_cost_optimization_opportunities
