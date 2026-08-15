-- source extract for fct_expenses (PII columns excluded by the MDL projection)
select expense_id, location_id, location_name, expense_category_id, category_name, is_operating_expense, is_cost_of_goods_sold, expense_description, vendor, expense_amount, incurred_date, expense_month
from main_marts.fct_expenses
