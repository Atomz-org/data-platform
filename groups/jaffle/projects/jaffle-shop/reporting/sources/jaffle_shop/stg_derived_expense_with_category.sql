-- source extract for stg_derived_expense_with_category (PII columns excluded by the MDL projection)
select expense_id, location_id, expense_category_id, category_name, incurred_date, expense_amount, expense_description
from main_marts.stg_derived_expense_with_category
