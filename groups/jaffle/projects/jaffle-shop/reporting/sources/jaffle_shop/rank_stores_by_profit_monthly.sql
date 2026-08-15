-- source extract for rank_stores_by_profit_monthly (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, estimated_profit, profit_rank, profit_share_pct, profit_quartile
from main_marts.rank_stores_by_profit_monthly
