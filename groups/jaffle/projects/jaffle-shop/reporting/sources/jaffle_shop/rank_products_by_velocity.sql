-- source extract for rank_products_by_velocity (PII columns excluded by the MDL projection)
select product_id, active_days, total_units, units_per_day, velocity_rank, velocity_quartile
from main_marts.rank_products_by_velocity
