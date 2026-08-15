-- source extract for rpt_ingredient_cost_impact (PII columns excluded by the MDL projection)
select price_month, menu_item_id, menu_item_name, menu_item_price, gross_margin, gross_margin_pct, total_cost_impact, ingredients_with_change, adjusted_margin, adjusted_margin_pct
from main_marts.rpt_ingredient_cost_impact
