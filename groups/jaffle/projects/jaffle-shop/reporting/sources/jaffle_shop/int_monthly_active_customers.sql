-- source extract for int_monthly_active_customers (PII columns excluded by the MDL projection)
select month_start, total_customer_visits, new_customers, returning_customer_visits, mom_customer_visit_change, mom_new_customer_change, total_orders, total_revenue, active_days_in_month, avg_daily_customers, prev_month_customer_visits, prev_month_new_customers
from main_marts.int_monthly_active_customers
