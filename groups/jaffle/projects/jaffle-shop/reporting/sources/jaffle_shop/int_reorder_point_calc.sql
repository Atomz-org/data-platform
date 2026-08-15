-- source extract for int_reorder_point_calc (PII columns excluded by the MDL projection)
select product_id, location_id, reorder_point, suggested_reorder_quantity, needs_reorder, current_quantity, daily_depletion_rate, estimated_days_of_stock, supplier_avg_lead_time_days
from main_marts.int_reorder_point_calc
