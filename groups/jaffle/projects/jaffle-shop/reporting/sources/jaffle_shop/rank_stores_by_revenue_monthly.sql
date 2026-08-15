-- source extract for rank_stores_by_revenue_monthly (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, monthly_orders, revenue_rank, revenue_dense_rank, revenue_share_pct, revenue_quartile
from main_marts.rank_stores_by_revenue_monthly
