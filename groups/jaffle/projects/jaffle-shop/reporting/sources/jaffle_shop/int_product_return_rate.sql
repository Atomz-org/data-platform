-- source extract for int_product_return_rate (PII columns excluded by the MDL projection)
select product_id, waste_rate_pct, waste_cost_as_pct_of_revenue, total_sold, total_revenue, total_wasted, total_waste_cost
from main_marts.int_product_return_rate
