-- source extract for wide_inventory_summary (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, inventory_value, safety_stock, inventory_turnover_ratio, stock_alert, reorder_point, estimated_days_of_stock, inventory_health
from main_marts.wide_inventory_summary
