-- source extract for trend_avg_basket_size (PII columns excluded by the MDL projection)
select order_date, avg_basket_size, order_count, total_items, basket_7d_ma, basket_28d_ma, basket_same_day_last_week, basket_trend_status
from main_marts.trend_avg_basket_size
