-- source extract for int_product_sales_velocity (PII columns excluded by the MDL projection)
select product_id, sale_date, velocity_7d, velocity_28d, velocity_ratio, is_spike_day, product_name, product_type, units_sold, order_count, daily_revenue, units_last_7d, units_last_28d
from main_marts.int_product_sales_velocity
