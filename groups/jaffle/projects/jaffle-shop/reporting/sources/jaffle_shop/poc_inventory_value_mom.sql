-- source extract for poc_inventory_value_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_value, prior_month_value, value_mom_pct, current_movement, prior_month_movement
from main_marts.poc_inventory_value_mom
