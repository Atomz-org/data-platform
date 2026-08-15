-- source extract for int_product_price_history_enriched (PII columns excluded by the MDL projection)
select pricing_history_id, product_id, price, period_start, period_end, days_at_price, units_during_period, avg_daily_units_at_price, point_elasticity_estimate, revenue_during_period, prior_price, prior_daily_units
from main_marts.int_product_price_history_enriched
