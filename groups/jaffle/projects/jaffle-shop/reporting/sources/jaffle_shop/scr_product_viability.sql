-- source extract for scr_product_viability (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    viability_score,
    viability_tier
from main_marts.scr_product_viability
