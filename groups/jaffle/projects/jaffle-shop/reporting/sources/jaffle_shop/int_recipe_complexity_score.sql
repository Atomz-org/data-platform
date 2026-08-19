-- source extract for int_recipe_complexity_score (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    recipe_id,
    complexity_score,
    complexity_tier
from main_marts.int_recipe_complexity_score
