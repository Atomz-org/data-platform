-- source extract for rank_products_by_volume_monthly (PII columns excluded by the MDL projection)
select month_start, product_id, monthly_units, monthly_revenue, volume_rank, volume_share_pct, volume_quintile
from main_marts.rank_products_by_volume_monthly
