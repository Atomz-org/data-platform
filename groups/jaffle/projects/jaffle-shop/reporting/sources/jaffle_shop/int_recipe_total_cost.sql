-- source extract for int_recipe_total_cost (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    recipe_id,
    ingredient_count,
    total_ingredient_cost,
    highest_ingredient_cost,
    lowest_ingredient_cost
from main_marts.int_recipe_total_cost
