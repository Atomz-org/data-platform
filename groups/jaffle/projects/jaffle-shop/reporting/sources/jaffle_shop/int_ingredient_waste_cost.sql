-- source extract for int_ingredient_waste_cost (PII columns excluded by the MDL projection)
select ingredient_id, ingredient_name, ingredient_category, is_perishable, usage_month, total_quantity_used, estimated_waste_quantity, avg_unit_cost, estimated_waste_cost, estimated_waste_pct, avg_daily_usage, peak_daily_usage, active_days
from main_marts.int_ingredient_waste_cost
