-- source extract for rpt_budget_variance (PII columns excluded by the MDL projection)
select budget_id, location_id, location_name, expense_category_id, budget_type, budget_month, budgeted_amount, actual_amount, variance_amount, variance_pct, variance_status, variance_severity
from main_marts.rpt_budget_variance
