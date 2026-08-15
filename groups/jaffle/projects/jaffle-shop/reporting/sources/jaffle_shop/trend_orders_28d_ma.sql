-- source extract for trend_orders_28d_ma (PII columns excluded by the MDL projection)
select revenue_date, location_id, order_count, orders_28d_ma, orders_28d_total, recency_rank
from main_marts.trend_orders_28d_ma
