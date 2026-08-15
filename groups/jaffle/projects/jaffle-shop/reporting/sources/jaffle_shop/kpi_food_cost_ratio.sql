-- source extract for kpi_food_cost_ratio (PII columns excluded by the MDL projection)
select usage_month, total_quantity_used, monthly_revenue, food_cost_ratio
from main_marts.kpi_food_cost_ratio
