-- source extract for trend_delivery_on_time (PII columns excluded by the MDL projection)
select actual_arrival_at, total_deliveries, on_time_deliveries, on_time_pct, on_time_7d_ma, on_time_28d_ma, delivery_performance_band
from main_marts.trend_delivery_on_time
