-- source extract for sum_weekly_product_totals (PII columns excluded by the MDL projection)
select week_start, product_id, weekly_units, weekly_revenue, avg_unit_price, prior_week_revenue
from main_marts.sum_weekly_product_totals
