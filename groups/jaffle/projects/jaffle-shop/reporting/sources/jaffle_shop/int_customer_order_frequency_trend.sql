-- source extract for int_customer_order_frequency_trend (PII columns excluded by the MDL projection)
select customer_id, order_month, monthly_order_count, order_count_3m_avg, monthly_trend_direction, trend_acceleration, monthly_spend, prior_month_orders
from main_marts.int_customer_order_frequency_trend
