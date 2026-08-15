-- source extract for rank_stores_by_growth_monthly (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, growth_pct, growth_rank, growth_quartile
from main_marts.rank_stores_by_growth_monthly
