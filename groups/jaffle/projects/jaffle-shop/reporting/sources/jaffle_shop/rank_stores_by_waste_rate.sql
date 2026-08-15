-- source extract for rank_stores_by_waste_rate (PII columns excluded by the MDL projection)
select month_start, location_id, waste_rate_pct, monthly_waste_cost, waste_rank_best_first, waste_quartile
from main_marts.rank_stores_by_waste_rate
