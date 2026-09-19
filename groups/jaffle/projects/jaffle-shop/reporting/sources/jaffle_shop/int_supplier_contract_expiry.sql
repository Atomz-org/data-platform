-- source extract for int_supplier_contract_expiry (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    contract_id,
    days_until_expiry,
    expiry_urgency
from main_marts.int_supplier_contract_expiry
