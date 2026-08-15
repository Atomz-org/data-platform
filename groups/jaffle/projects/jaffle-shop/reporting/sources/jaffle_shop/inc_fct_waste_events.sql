-- source extract for inc_fct_waste_events (PII columns excluded by the MDL projection)
select waste_event_id, product_id, location_id, wasted_at, quantity_wasted, waste_reason, cost_of_waste, waste_month
from main_marts.inc_fct_waste_events
