-- source extract for int_inventory_level_weekly_snapshot (PII columns excluded by the MDL projection)
select week_end_date, product_id, location_id, end_of_week_balance, weekly_inbound, weekly_outbound, movement_count, product_name, location_name
from main_marts.int_inventory_level_weekly_snapshot
