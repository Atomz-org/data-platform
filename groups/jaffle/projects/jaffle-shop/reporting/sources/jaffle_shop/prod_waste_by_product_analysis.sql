-- source extract for prod_waste_by_product_analysis (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, waste_month, total_waste_qty, total_cost_of_waste, waste_events, monthly_qty_sold, waste_rate_pct, cost_of_waste_pct_of_revenue
from main_marts.prod_waste_by_product_analysis
