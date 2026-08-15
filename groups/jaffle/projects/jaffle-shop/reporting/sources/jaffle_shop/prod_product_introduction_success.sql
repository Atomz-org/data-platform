-- source extract for prod_product_introduction_success (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, launch_date, first_90_day_qty, first_90_day_revenue, active_sale_days, avg_90_day_qty, launch_status
from main_marts.prod_product_introduction_success
