-- source extract for kpi_customer_churn_rate (PII columns excluded by the MDL projection)
select month_start, tracked_active_customers, churned_customers, churn_rate_pct, prior_month_churn
from main_marts.kpi_customer_churn_rate
