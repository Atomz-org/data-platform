-- source extract for int_ingredient_cost_trend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    ingredient_id,
    price_month,
    avg_unit_cost,
    min_unit_cost,
    max_unit_cost,
    prev_month_avg_cost,
    mom_cost_change_pct
from main_marts.int_ingredient_cost_trend
