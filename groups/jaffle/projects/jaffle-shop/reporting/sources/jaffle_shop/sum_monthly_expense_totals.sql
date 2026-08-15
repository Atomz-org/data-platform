-- source extract for sum_monthly_expense_totals (PII columns excluded by the MDL projection)
select expense_month, expense_category_id, total_expense_amount, expense_count, avg_expense_amount, prior_month_amount
from main_marts.sum_monthly_expense_totals
