-- source extract for poc_labor_cost_yoy (PII columns excluded by the MDL projection)
select month_start, location_id, current_cost, prior_year_cost, labor_cost_yoy_pct
from main_marts.poc_labor_cost_yoy
