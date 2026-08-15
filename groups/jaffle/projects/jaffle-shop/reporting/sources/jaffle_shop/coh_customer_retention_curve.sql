-- source extract for coh_customer_retention_curve (PII columns excluded by the MDL projection)
select cohort_month, months_since_first_order, cohort_size, active_customers, retention_rate_pct
from main_marts.coh_customer_retention_curve
