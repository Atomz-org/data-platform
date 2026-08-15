-- source extract for met_daily_revenue_by_store (PII columns excluded by the MDL projection)
select revenue_date, location_id, store_name, total_revenue, revenue_7d_avg, revenue_28d_avg, order_count, avg_order_value, gross_revenue, tax_collected, orders_7d_avg, orders_28d_avg
from main_marts.met_daily_revenue_by_store
