-- source extract for adv_customer_analysis_cube (PII columns excluded by the MDL projection)
select customer_type, location_id, order_year, total_orders, unique_customers, total_revenue, avg_order_value, total_items_sold, is_type_aggregated, is_location_aggregated, is_year_aggregated, cube_level
from main_marts.adv_customer_analysis_cube
