-- source extract for prod_menu_price_competitiveness (PII columns excluded by the MDL projection)
select menu_item_id, item_name, current_price, category_name, category_avg_price, category_min_price, category_max_price, price_vs_category_avg, price_positioning
from main_marts.prod_menu_price_competitiveness
