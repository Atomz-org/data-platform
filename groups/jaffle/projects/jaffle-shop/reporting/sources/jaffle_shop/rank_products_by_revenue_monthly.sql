-- source extract for rank_products_by_revenue_monthly (PII columns excluded by the MDL projection)
select month_start, product_id, monthly_revenue, monthly_units, revenue_rank, revenue_share_pct, revenue_quintile
from main_marts.rank_products_by_revenue_monthly
