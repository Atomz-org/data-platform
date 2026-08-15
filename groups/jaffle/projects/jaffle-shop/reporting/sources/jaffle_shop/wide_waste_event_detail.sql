-- source extract for wide_waste_event_detail (PII columns excluded by the MDL projection)
select waste_log_id, product_id, product_name, product_type, location_id, store_name, wasted_at, quantity_wasted, cost_of_waste, waste_reason, cost_per_unit_wasted, waste_month
from main_marts.wide_waste_event_detail
