-- source extract for rpt_menu_engineering_matrix (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, menu_item_id, menu_item_name, category_name, menu_item_price, total_ingredient_cost, gross_margin, gross_margin_pct, total_units_sold, total_revenue, total_gross_profit, avg_category_volume, avg_category_margin_pct, menu_engineering_class, recommended_action
from main_marts.rpt_menu_engineering_matrix
