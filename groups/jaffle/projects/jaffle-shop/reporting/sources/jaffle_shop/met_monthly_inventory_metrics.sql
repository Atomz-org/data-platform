-- source extract for met_monthly_inventory_metrics (PII columns excluded by the MDL projection)
select month_start, location_id, mom_movement_change, location_name, monthly_movements, monthly_inbound, monthly_outbound, avg_daily_products_moved, products_in_stock, total_units_on_hand, prev_month_movements
from main_marts.met_monthly_inventory_metrics
