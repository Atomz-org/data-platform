-- source extract for int_product_sales_daily (PII columns excluded by the MDL projection)
select sale_date, product_id, product_name, product_type, units_sold, order_count, daily_revenue, current_unit_price
from main_marts.int_product_sales_daily
