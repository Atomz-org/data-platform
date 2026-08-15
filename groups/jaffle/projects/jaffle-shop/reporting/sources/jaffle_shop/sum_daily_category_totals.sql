-- source extract for sum_daily_category_totals (PII columns excluded by the MDL projection)
select sale_date, category, total_quantity, total_revenue, active_products
from main_marts.sum_daily_category_totals
