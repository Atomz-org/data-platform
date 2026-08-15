-- source extract for dim_expense_categories (PII columns excluded by the MDL projection)
select expense_category_id, category_name, category_description, is_operating_expense, is_cost_of_goods_sold, expense_classification
from main_marts.dim_expense_categories
