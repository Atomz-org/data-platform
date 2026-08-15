-- source extract for rpt_menu_profitability (PII columns excluded by the MDL projection)
select menu_item_id, menu_item_name, menu_item_price, category_name, product_type, total_ingredient_cost, gross_margin, gross_margin_pct, total_units_sold, total_revenue, total_gross_profit, margin_tier
from main_marts.rpt_menu_profitability
