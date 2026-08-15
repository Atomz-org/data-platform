-- source extract for coh_employee_tenure_cohort (PII columns excluded by the MDL projection)
select hire_quarter, cohort_size, still_active, retention_rate_pct, avg_tenure_days, max_tenure_days, left_within_6_months, departments_represented
from main_marts.coh_employee_tenure_cohort
