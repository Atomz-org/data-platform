-- source extract for met_daily_product_sales (PII columns excluded by the MDL projection)
select sale_date, product_id, daily_margin, product_name, product_type, units_sold, order_count, daily_revenue, unit_margin, margin_pct
from main_marts.met_daily_product_sales
