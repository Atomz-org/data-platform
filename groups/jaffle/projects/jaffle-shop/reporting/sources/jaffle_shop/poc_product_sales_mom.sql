-- source extract for poc_product_sales_mom (PII columns excluded by the MDL projection)
select month_start, product_id, current_qty, current_revenue, prior_month_qty, prior_month_revenue, qty_mom_change_pct, revenue_mom_change_pct
from main_marts.poc_product_sales_mom
