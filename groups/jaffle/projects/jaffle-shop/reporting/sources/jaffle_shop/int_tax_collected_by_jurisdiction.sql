-- source extract for int_tax_collected_by_jurisdiction (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    jurisdiction,
    tax_type,
    tax_rate_pct,
    location_id,
    tax_month,
    taxable_amount,
    tax_collected
from main_marts.int_tax_collected_by_jurisdiction
