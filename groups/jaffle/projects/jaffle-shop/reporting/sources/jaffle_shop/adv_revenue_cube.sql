-- source extract for adv_revenue_cube (PII columns excluded by the MDL projection)
select location_id, location_name, product_id, product_name, sale_month, total_revenue, total_orders, is_location_aggregated, is_product_aggregated, is_month_aggregated, aggregation_level
from main_marts.adv_revenue_cube
