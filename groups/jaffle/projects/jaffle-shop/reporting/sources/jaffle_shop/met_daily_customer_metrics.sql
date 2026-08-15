-- source extract for met_daily_customer_metrics (PII columns excluded by the MDL projection)
select activity_date, active_customers, new_customers, returning_customers, total_orders, total_revenue, orders_per_customer, revenue_per_customer, new_customers_7d_avg, active_customers_7d_avg
from main_marts.met_daily_customer_metrics
