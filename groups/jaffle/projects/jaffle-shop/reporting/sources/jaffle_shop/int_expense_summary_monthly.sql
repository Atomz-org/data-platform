-- source extract for int_expense_summary_monthly (PII columns excluded by the MDL projection)
select location_id, expense_category_id, category_name, expense_month, expense_count, total_expense_amount, avg_expense_amount, is_operating_expense, is_cost_of_goods_sold, min_expense_amount, max_expense_amount
from main_marts.int_expense_summary_monthly
