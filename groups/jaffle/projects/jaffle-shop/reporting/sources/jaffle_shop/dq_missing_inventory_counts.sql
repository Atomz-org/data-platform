-- source extract for dq_missing_inventory_counts (PII columns excluded by the MDL projection)
select product_id, location_id, count_status, product_name, location_name, last_movement_at
from main_marts.dq_missing_inventory_counts
