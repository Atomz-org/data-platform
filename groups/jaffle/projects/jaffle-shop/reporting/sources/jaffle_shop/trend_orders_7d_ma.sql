-- source extract for trend_orders_7d_ma (PII columns excluded by the MDL projection)
select revenue_date, location_id, order_count, orders_7d_ma, orders_deviation_7d, volume_flag
from main_marts.trend_orders_7d_ma
