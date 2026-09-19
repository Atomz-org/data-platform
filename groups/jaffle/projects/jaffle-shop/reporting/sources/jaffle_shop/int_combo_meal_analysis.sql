-- source extract for int_combo_meal_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_a,
    product_b,
    co_occurrence_count
from main_marts.int_combo_meal_analysis
