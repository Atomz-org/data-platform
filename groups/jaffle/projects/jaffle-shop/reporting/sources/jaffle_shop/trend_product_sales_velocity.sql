-- source extract for trend_product_sales_velocity (PII columns excluded by the MDL projection)
select sale_date, product_id, units_sold, daily_revenue, qty_7d_ma, qty_28d_ma, velocity_trend
from main_marts.trend_product_sales_velocity
