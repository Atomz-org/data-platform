-- source extract for rank_products_by_margin (PII columns excluded by the MDL projection)
select product_id, total_revenue, total_cogs, gross_margin_pct, margin_rank, margin_quartile, margin_band
from main_marts.rank_products_by_margin
