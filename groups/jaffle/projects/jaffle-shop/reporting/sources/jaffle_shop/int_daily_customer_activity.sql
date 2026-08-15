-- source extract for int_daily_customer_activity (PII columns excluded by the MDL projection)
select activity_date, unique_customers, new_customers, returning_customers, total_orders, total_revenue
from main_marts.int_daily_customer_activity
