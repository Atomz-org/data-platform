-- source extract for prod_product_velocity_segments (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, daily_sales_velocity, monthly_sales_velocity, velocity_segment, inventory_recommendation
from main_marts.prod_product_velocity_segments
