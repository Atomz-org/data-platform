-- source extract for fct_product_sales (PII columns excluded by the MDL projection)
select sale_date, product_id, product_name, product_type, current_unit_price, units_sold, order_count, daily_revenue, cumulative_revenue, rolling_7d_avg_units
from main_marts.fct_product_sales
