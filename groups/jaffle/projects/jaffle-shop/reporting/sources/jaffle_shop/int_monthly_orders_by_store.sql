-- source extract for int_monthly_orders_by_store (PII columns excluded by the MDL projection)
select month_start, location_id, order_count, total_revenue, mom_revenue_growth, yoy_revenue_growth, location_name, unique_customer_visits, total_subtotal, avg_daily_order_value, active_days_in_month, prev_month_revenue, same_month_last_year_revenue
from main_marts.int_monthly_orders_by_store
