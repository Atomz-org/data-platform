-- source extract for poc_expense_mom_by_category (PII columns excluded by the MDL projection)
select expense_month, expense_category_id, current_amount, prior_month_amount, current_count, prior_month_count, expense_mom_pct
from main_marts.poc_expense_mom_by_category
