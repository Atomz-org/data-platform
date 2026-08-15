-- source extract for met_weekly_inventory_metrics (PII columns excluded by the MDL projection)
select week_start, location_id, location_name, weekly_movements, weekly_inbound, weekly_outbound, avg_daily_products_moved, products_in_stock, total_units_on_hand
from main_marts.met_weekly_inventory_metrics
