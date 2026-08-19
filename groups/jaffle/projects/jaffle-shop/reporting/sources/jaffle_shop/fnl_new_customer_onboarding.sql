-- source extract for fnl_new_customer_onboarding (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    cohort_month,
    stage_1_first_order,
    stage_2_second_within_30d,
    stage_3_third_order,
    second_order_rate_pct,
    avg_days_to_second_order
from main_marts.fnl_new_customer_onboarding
