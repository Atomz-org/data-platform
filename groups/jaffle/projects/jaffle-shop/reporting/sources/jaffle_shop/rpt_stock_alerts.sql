-- source extract for rpt_stock_alerts (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, daily_depletion_rate, estimated_days_of_stock, supplier_avg_lead_time_days, reorder_point, suggested_reorder_quantity, needs_reorder, stock_alert_level, last_movement_at
from main_marts.rpt_stock_alerts
