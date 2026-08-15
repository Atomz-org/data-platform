-- source extract for ml_feature_pricing_optimization (PII columns excluded by the MDL projection)
select product_id, current_unit_price, unit_cost, margin_pct, avg_daily_volume, estimated_price_elasticity, product_name, unit_margin, total_volume, total_revenue, active_sale_days, price_change_count, avg_price_change_pct
from main_marts.ml_feature_pricing_optimization
