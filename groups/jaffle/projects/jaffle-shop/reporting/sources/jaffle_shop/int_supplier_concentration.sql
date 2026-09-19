-- source extract for int_supplier_concentration (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    supplier_name,
    lifetime_spend,
    avg_spend_share_pct,
    max_spend_share_pct,
    active_months
from main_marts.int_supplier_concentration
