-- source extract for int_payroll_tax_by_jurisdiction (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    payroll_month,
    total_gross_pay,
    effective_deduction_rate_pct
from main_marts.int_payroll_tax_by_jurisdiction
