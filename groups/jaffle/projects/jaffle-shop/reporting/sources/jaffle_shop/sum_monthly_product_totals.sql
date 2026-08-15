-- source extract for sum_monthly_product_totals (PII columns excluded by the MDL projection)
select month_start, product_id, monthly_units, monthly_revenue, avg_unit_price, prior_month_revenue, mom_change_pct, revenue_rank
from main_marts.sum_monthly_product_totals
