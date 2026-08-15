-- source extract for met_monthly_product_sales (PII columns excluded by the MDL projection)
select month_start, product_id, mom_revenue_growth, product_name, product_type, monthly_units, monthly_orders, monthly_revenue, monthly_margin, margin_pct, prev_month_revenue
from main_marts.met_monthly_product_sales
