-- source extract for rpt_customer_cohort_retention (PII columns excluded by the MDL projection)
select cohort_month, cohort_size, months_since_first_order, active_customers, retention_rate_pct, churned_customers, churn_rate_pct
from main_marts.rpt_customer_cohort_retention
