-- source extract for int_ingredient_usage_variance (PII columns excluded by the MDL projection)
select product_id, usage_date, usage_variance, variance_pct, ingredient_id, actual_units_used, expected_ingredient_usage
from main_marts.int_ingredient_usage_variance
