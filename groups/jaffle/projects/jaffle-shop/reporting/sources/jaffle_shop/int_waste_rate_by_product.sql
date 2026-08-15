-- source extract for int_waste_rate_by_product (PII columns excluded by the MDL projection)
select product_id, total_waste_events, total_quantity_wasted, total_cost_of_waste, waste_rate, avg_quantity_per_event, first_waste_at, last_waste_at, total_inbound_quantity
from main_marts.int_waste_rate_by_product
