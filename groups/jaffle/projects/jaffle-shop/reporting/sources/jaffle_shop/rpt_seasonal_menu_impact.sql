-- source extract for rpt_seasonal_menu_impact (PII columns excluded by the MDL projection)
select product_id, product_name, season_name, promotion_name, promotion_start_date, promotion_end_date, promo_active_days, promo_units_sold, promo_revenue, promo_avg_daily_units, baseline_avg_daily_units, sales_lift_pct, promotion_effectiveness
from main_marts.rpt_seasonal_menu_impact
