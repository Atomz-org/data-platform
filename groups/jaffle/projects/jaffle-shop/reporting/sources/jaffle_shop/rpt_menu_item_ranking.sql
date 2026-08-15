-- source extract for rpt_menu_item_ranking (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, menu_category_id, category_name, total_units_sold, total_revenue, volume_rank_in_category, revenue_rank_in_category, overall_volume_rank, overall_revenue_rank, menu_item_price, total_ingredient_cost, gross_margin, gross_margin_pct, total_gross_profit, profit_rank_in_category
from main_marts.rpt_menu_item_ranking
