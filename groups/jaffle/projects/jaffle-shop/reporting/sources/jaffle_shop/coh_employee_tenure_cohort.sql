-- source extract for coh_employee_tenure_cohort (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    hire_quarter,
    cohort_size,
    still_active,
    retention_rate_pct,
    avg_tenure_days
from main_marts.coh_employee_tenure_cohort
