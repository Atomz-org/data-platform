-- source extract for prod_limited_time_offer_analysis (PII columns excluded by the MDL projection)
select menu_item_id, season_name, promotion_name, promotion_start_date, promotion_end_date, promo_duration_days, total_qty_during_promo, daily_revenue_during_promo, active_sale_days, avg_daily_qty, performance_vs_permanent_ratio
from main_marts.prod_limited_time_offer_analysis
