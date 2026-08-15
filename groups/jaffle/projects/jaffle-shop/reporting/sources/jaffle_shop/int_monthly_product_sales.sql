-- source extract for int_monthly_product_sales (PII columns excluded by the MDL projection)
select month_start, product_id, product_name, units_sold, monthly_revenue, mom_revenue_growth, product_type, order_count, avg_daily_units, active_days_in_month, prev_month_revenue
from main_marts.int_monthly_product_sales
