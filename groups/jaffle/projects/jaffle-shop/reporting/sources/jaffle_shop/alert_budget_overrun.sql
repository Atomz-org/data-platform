-- source extract for alert_budget_overrun (PII columns excluded by the MDL projection)
select budget_month, location_id, expense_category_id, budgeted_amount, actual_amount, overrun_amount, overrun_pct, alert_type, severity
from main_marts.alert_budget_overrun
