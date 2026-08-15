-- source extract for int_product_sales_by_location (PII columns excluded by the MDL projection)
select location_id, location_name, sale_date, product_id, product_name, product_type, units_sold, daily_revenue
from main_marts.int_product_sales_by_location
