-- source extract for view_cfo_budget_status (PII columns excluded by the MDL projection)
select budget_month, location_id, expense_category_id, budgeted_amount, actual_amount, variance_amount, variance_pct, budget_status
from main_marts.view_cfo_budget_status
