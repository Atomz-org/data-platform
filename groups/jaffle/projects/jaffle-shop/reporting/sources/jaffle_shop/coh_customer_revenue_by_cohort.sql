-- source extract for coh_customer_revenue_by_cohort (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    cohort_month,
    months_since_first_order,
    period_revenue,
    cumulative_revenue,
    revenue_per_active_customer
from main_marts.coh_customer_revenue_by_cohort
