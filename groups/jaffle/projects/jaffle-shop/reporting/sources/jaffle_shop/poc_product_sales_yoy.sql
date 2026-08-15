-- source extract for poc_product_sales_yoy (PII columns excluded by the MDL projection)
select month_start, product_id, current_qty, current_revenue, prior_year_qty, prior_year_revenue, qty_yoy_change_pct, revenue_yoy_change_pct
from main_marts.poc_product_sales_yoy
