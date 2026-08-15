-- source extract for fin_revenue_by_daypart (PII columns excluded by the MDL projection)
select location_id, store_name, daypart, revenue_month, order_count, total_revenue, avg_order_value, avg_daily_orders
from main_marts.fin_revenue_by_daypart
