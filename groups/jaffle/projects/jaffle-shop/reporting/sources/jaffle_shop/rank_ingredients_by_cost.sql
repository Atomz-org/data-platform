-- source extract for rank_ingredients_by_cost (PII columns excluded by the MDL projection)
select ingredient_id, total_cost, total_quantity, avg_unit_cost, cost_rank, cost_share_pct, cumulative_cost
from main_marts.rank_ingredients_by_cost
