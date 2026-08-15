-- source extract for sum_monthly_category_totals (PII columns excluded by the MDL projection)
select sale_month, category, total_quantity, total_revenue, active_products, revenue_share_pct
from main_marts.sum_monthly_category_totals
