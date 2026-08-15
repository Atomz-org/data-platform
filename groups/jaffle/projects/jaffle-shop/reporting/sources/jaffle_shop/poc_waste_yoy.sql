-- source extract for poc_waste_yoy (PII columns excluded by the MDL projection)
select month_start, location_id, current_waste, prior_year_waste, waste_yoy_pct
from main_marts.poc_waste_yoy
