-- source extract for int_supplier_payment_aging (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    avg_days_payable_outstanding,
    total_outstanding
from main_marts.int_supplier_payment_aging
