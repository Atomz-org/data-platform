-- source extract for int_expense_by_revenue_ratio (PII columns excluded by the MDL projection)
select location_id, expense_month, expense_to_revenue_pct, category_name, total_expense_amount, monthly_revenue
from main_marts.int_expense_by_revenue_ratio
