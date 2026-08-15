-- source extract for int_weekly_orders_by_store (PII columns excluded by the MDL projection)
select week_start, location_id, order_count, total_revenue, active_days_in_week, location_name, unique_customer_visits, total_subtotal, avg_daily_order_value
from main_marts.int_weekly_orders_by_store
