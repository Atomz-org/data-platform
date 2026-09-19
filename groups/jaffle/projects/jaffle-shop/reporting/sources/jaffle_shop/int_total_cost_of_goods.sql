-- source extract for int_total_cost_of_goods (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    total_cogs_per_unit,
    ingredient_cost_share_pct
from main_marts.int_total_cost_of_goods
