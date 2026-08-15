-- source extract for rank_stores_by_labor_efficiency (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_labor_cost, monthly_revenue, revenue_per_labor_dollar, efficiency_rank, efficiency_quartile
from main_marts.rank_stores_by_labor_efficiency
