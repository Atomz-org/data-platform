-- source extract for dq_revenue_expense_mismatch (PII columns excluded by the MDL projection)
select check_date, expense_to_revenue_ratio, anomaly_type, daily_revenue, daily_expenses
from main_marts.dq_revenue_expense_mismatch
