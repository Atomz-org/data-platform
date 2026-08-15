-- source extract for rpt_reorder_recommendation (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, location_id, location_name, current_quantity, stock_alert_level, reorder_point, suggested_reorder_quantity, daily_depletion_rate, estimated_days_of_stock, supplier_avg_lead_time_days, recommended_order_quantity, priority_rank
from main_marts.rpt_reorder_recommendation
