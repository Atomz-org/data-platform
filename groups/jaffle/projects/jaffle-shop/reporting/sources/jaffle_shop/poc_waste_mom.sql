-- source extract for poc_waste_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_waste, prior_month_waste, current_events, prior_month_events, waste_cost_mom_pct, waste_trend
from main_marts.poc_waste_mom
