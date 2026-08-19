-- source extract for fnl_loyalty_enrollment (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    stage_1_total_customers,
    stage_2_loyalty_signups,
    stage_3_first_earn,
    stage_4_first_redemption,
    overall_conversion_pct
from main_marts.fnl_loyalty_enrollment
