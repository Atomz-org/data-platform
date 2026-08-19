-- source extract for coh_customer_monthly_cohort (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    cohort_month,
    order_month,
    months_since_first_order,
    monthly_orders,
    monthly_revenue
from main_marts.coh_customer_monthly_cohort
