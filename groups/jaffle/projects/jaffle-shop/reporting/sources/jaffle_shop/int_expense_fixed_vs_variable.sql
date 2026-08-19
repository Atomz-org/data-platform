-- source extract for int_expense_fixed_vs_variable (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    expense_category_id,
    expense_classification,
    coefficient_of_variation
from main_marts.int_expense_fixed_vs_variable
