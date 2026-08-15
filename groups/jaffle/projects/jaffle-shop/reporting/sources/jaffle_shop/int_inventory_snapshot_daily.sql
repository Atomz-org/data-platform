-- source extract for int_inventory_snapshot_daily (PII columns excluded by the MDL projection)
select product_id, location_id, counted_on_hand, system_quantity, count_variance, counted_reserved, counted_available, last_count_date, last_movement_at
from main_marts.int_inventory_snapshot_daily
