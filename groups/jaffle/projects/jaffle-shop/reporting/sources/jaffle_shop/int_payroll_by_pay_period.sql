-- source extract for int_payroll_by_pay_period (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    pay_period_start,
    pay_period_end,
    total_gross_pay,
    deduction_rate_pct,
    overtime_pct
from main_marts.int_payroll_by_pay_period
