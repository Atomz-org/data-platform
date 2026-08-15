-- source extract for rev_etl_inventory_reorder (PII columns excluded by the MDL projection)
select location_id, product_id, current_quantity, reorder_point, suggested_reorder_quantity, estimated_days_of_stock, stock_alert_level, exported_at, reorder_trigger
from main_marts.rev_etl_inventory_reorder
