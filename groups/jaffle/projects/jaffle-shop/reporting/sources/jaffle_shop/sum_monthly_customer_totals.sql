-- source extract for sum_monthly_customer_totals (PII columns excluded by the MDL projection)
select month_start, tracked_active_customers, new_customers, churned_customers, retention_rate_pct, prior_month_customers
from main_marts.sum_monthly_customer_totals
