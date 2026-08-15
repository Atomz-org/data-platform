-- source extract for sum_daily_product_totals (PII columns excluded by the MDL projection)
select sale_date, product_id, units_sold, daily_revenue, avg_unit_price, cumulative_revenue
from main_marts.sum_daily_product_totals
