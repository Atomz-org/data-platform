-- source extract for int_budget_vs_actual (PII columns excluded by the MDL projection)
select budget_id, location_id, budget_type, budget_month, budgeted_amount, actual_amount, variance_amount, variance_pct, expense_category_id
from main_marts.int_budget_vs_actual
