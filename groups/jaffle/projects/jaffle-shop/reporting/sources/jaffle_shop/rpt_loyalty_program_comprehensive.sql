-- source extract for rpt_loyalty_program_comprehensive (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    report_month,
    new_enrollments,
    monthly_redemption_rate
from main_marts.rpt_loyalty_program_comprehensive
