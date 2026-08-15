-- source extract for sc_waste_root_cause (PII columns excluded by the MDL projection)
select waste_month, location_id, waste_reason, waste_event_count, total_quantity_wasted, total_cost_of_waste, avg_cost_of_waste_per_event, root_cause_category
from main_marts.sc_waste_root_cause
