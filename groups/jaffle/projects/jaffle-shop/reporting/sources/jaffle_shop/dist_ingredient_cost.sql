-- source extract for dist_ingredient_cost (PII columns excluded by the MDL projection)
select ingredient_id, mean_ingredient_unit_cost, median_cost, p90_cost, min_cost, max_cost, usage_records
from main_marts.dist_ingredient_cost
