-- source extract for inc_met_daily_product_sales (PII columns excluded by the MDL projection)
select product_sales_key, store_id, product_id, sale_date, total_quantity, total_cost, order_count
from main_marts.inc_met_daily_product_sales
