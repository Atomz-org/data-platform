-- source extract for adv_dynamic_pricing_recommendation (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, current_unit_price, total_ingredient_cost, gross_margin, gross_margin_pct, total_units_sold, avg_daily_units, velocity_tier, margin_tier, pricing_recommendation, suggested_adjustment_pct, suggested_price, action_priority, days_with_sales, last_sale_date
from main_marts.adv_dynamic_pricing_recommendation
