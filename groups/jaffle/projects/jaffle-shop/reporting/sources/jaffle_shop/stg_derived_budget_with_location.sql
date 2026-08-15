-- source extract for stg_derived_budget_with_location (PII columns excluded by the MDL projection)
select budget_id, location_id, location_name, expense_category_id, budget_month, budgeted_amount
from main_marts.stg_derived_budget_with_location
