-- source extract for poc_labor_cost_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_cost, prior_month_cost, current_hours, prior_month_hours, labor_cost_mom_pct, hours_mom_pct
from main_marts.poc_labor_cost_mom
