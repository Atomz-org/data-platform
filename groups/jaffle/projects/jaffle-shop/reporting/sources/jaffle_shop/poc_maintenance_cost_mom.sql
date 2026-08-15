-- source extract for poc_maintenance_cost_mom (PII columns excluded by the MDL projection)
select maint_month, location_id, current_cost, prior_month_cost, current_events, prior_month_events, cost_mom_pct
from main_marts.poc_maintenance_cost_mom
