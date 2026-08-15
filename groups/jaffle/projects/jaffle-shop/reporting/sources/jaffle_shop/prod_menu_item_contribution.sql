-- source extract for prod_menu_item_contribution (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, total_qty, daily_revenue, total_margin_contribution, gross_margin_pct, revenue_contribution_pct, profit_contribution_pct, revenue_rank, profit_rank
from main_marts.prod_menu_item_contribution
