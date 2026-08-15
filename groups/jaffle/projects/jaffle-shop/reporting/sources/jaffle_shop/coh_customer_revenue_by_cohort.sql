-- source extract for coh_customer_revenue_by_cohort (PII columns excluded by the MDL projection)
select cohort_month, months_since_first_order, period_revenue, cumulative_revenue, revenue_per_active_customer, active_customers
from main_marts.coh_customer_revenue_by_cohort
