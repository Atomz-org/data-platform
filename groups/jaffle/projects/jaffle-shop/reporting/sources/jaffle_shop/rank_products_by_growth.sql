-- source extract for rank_products_by_growth (PII columns excluded by the MDL projection)
select month_start, product_id, monthly_revenue, growth_pct, growth_rank
from main_marts.rank_products_by_growth
