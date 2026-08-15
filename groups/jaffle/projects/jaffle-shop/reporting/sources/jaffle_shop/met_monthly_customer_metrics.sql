-- source extract for met_monthly_customer_metrics (PII columns excluded by the MDL projection)
select month_start, active_pct, churn_pct, total_customer_visits, total_orders, total_revenue, new_customers, returning_customer_visits, avg_daily_customers, mom_customer_visit_change, mom_new_customer_change, total_tracked_customers, tracked_active_customers, dormant_customers, churned_customers
from main_marts.met_monthly_customer_metrics
