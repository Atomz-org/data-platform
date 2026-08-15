-- source extract for kpi_customer_retention_rate (PII columns excluded by the MDL projection)
select month_start, tracked_active_customers, retention_rate_pct, prior_month_rate
from main_marts.kpi_customer_retention_rate
