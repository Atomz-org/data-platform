-- source extract for int_expense_fixed_vs_variable (PII columns excluded by the MDL projection)
select location_id, expense_category_id, expense_classification, coefficient_of_variation, category_name, avg_monthly_expense, stddev_expense
from main_marts.int_expense_fixed_vs_variable
