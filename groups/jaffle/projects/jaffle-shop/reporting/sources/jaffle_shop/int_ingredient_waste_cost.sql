-- source extract for int_ingredient_waste_cost (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    ingredient_id,
    ingredient_name,
    ingredient_category,
    is_perishable,
    usage_month,
    total_quantity_used,
    estimated_waste_quantity,
    avg_unit_cost,
    estimated_waste_cost,
    estimated_waste_pct
from main_marts.int_ingredient_waste_cost
