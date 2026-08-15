-- source extract for view_store_mgr_inventory_status (PII columns excluded by the MDL projection)
select location_id, product_id, current_quantity, reorder_point, estimated_days_of_stock, stock_alert_level, urgency, action_needed
from main_marts.view_store_mgr_inventory_status
