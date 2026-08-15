-- source extract for adv_expense_rollup (PII columns excluded by the MDL projection)
select location_id, location_name, expense_category_id, category_name, expense_month, total_expense, expense_count, avg_expense_amount, is_location_rolled, is_category_rolled, is_month_rolled, rollup_level
from main_marts.adv_expense_rollup
