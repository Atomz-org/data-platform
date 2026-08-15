-- source extract for int_budget_utilization_rate (PII columns excluded by the MDL projection)
select budget_id, utilization_rate_pct, budget_status, location_id, expense_category_id, budget_month, budgeted_amount, actual_spend, budget_remaining
from main_marts.int_budget_utilization_rate
