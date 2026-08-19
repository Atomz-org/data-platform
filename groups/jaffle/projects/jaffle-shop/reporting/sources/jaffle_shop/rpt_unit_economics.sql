-- source extract for rpt_unit_economics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    gross_margin_pct,
    contribution_tier
from main_marts.rpt_unit_economics
