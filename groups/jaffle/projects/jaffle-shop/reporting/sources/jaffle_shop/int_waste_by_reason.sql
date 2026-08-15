-- source extract for int_waste_by_reason (PII columns excluded by the MDL projection)
select waste_reason, total_quantity_wasted, total_waste_cost, location_id, waste_month, waste_event_count, avg_waste_cost_per_event, distinct_products_wasted
from main_marts.int_waste_by_reason
