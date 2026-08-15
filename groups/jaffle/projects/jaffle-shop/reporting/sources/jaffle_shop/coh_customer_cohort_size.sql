-- source extract for coh_customer_cohort_size (PII columns excluded by the MDL projection)
select cohort_month, new_customers, cumulative_customers, cohort_number
from main_marts.coh_customer_cohort_size
