-- source extract for met_weekly_product_sales (PII columns excluded by the MDL projection)
select week_start, product_id, wow_revenue_growth, product_name, product_type, weekly_units, weekly_orders, weekly_revenue, weekly_margin, margin_pct, prev_week_revenue
from main_marts.met_weekly_product_sales
