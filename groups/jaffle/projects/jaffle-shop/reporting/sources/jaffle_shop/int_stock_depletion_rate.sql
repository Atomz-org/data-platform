-- source extract for int_stock_depletion_rate (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, daily_depletion_rate, estimated_days_of_stock, outbound_last_30d, outbound_events_last_30d
from main_marts.int_stock_depletion_rate
