-- source extract for met_daily_inventory_metrics (PII columns excluded by the MDL projection)
select movement_date, location_id, total_movements, location_name, inbound_quantity, outbound_quantity, distinct_products_moved, products_in_stock, total_units_on_hand
from main_marts.met_daily_inventory_metrics
