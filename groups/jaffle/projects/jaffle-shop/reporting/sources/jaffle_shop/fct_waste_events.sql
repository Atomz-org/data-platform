-- source extract for fct_waste_events (PII columns excluded by the MDL projection)
select waste_log_id, product_id, product_name, product_type, location_id, location_name, waste_reason, quantity_wasted, cost_of_waste, wasted_at
from main_marts.fct_waste_events
