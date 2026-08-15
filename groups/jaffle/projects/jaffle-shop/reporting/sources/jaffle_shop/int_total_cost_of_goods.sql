-- source extract for int_total_cost_of_goods (PII columns excluded by the MDL projection)
select product_id, total_cogs_per_unit, ingredient_cost_share_pct, ingredient_cost_per_unit, supply_cost_per_unit, supply_count
from main_marts.int_total_cost_of_goods
