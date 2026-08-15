-- source extract for view_cfo_expense_overview (PII columns excluded by the MDL projection)
select expense_month, expense_category_id, category_name, location_id, total_amount, transaction_count, pct_of_monthly_total
from main_marts.view_cfo_expense_overview
