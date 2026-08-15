-- source extract for sum_quarterly_expense_totals (PII columns excluded by the MDL projection)
select expense_quarter, expense_category_id, quarterly_amount, quarterly_count, avg_expense
from main_marts.sum_quarterly_expense_totals
