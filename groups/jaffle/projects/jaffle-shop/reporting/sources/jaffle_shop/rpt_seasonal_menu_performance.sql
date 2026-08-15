-- source extract for rpt_seasonal_menu_performance (PII columns excluded by the MDL projection)
select product_id, product_name, is_seasonal, category_name, menu_item_price, season_name, promotion_name, promo_units_sold, promo_revenue, promo_avg_daily_units, non_promo_units_sold, non_promo_revenue, non_promo_avg_daily_units, total_units_sold, total_revenue, promotion_lift_pct, item_promotion_status, promotion_performance
from main_marts.rpt_seasonal_menu_performance
