-- source extract for prod_product_profitability_rank (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, total_qty, total_revenue, gross_margin, gross_margin_pct, total_contribution_margin, profitability_rank, total_all_products_margin, profit_share_pct, cumulative_profit_share_pct
from main_marts.prod_product_profitability_rank
