-- source extract for scr_supplier_reliability (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    supplier_id,
    reliability_score,
    reliability_tier
from main_marts.scr_supplier_reliability
