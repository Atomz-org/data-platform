-- source extract for coh_customer_cohort_size (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    cohort_month,
    new_customers,
    cumulative_customers
from main_marts.coh_customer_cohort_size
