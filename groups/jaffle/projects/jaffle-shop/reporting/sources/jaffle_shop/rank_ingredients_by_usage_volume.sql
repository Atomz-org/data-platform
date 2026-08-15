-- source extract for rank_ingredients_by_usage_volume (PII columns excluded by the MDL projection)
select ingredient_id, total_usage, active_days, usage_per_day, usage_rank, usage_quintile
from main_marts.rank_ingredients_by_usage_volume
