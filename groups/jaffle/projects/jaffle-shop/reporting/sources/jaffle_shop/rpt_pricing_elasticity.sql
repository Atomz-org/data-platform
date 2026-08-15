-- source extract for rpt_pricing_elasticity (PII columns excluded by the MDL projection)
select pricing_history_id, product_id, product_name, product_type, old_price, new_price, price_change_amount, price_change_pct, price_change_direction, change_reason, price_changed_date, avg_daily_units_before, avg_daily_units_after, volume_change_pct, price_elasticity
from main_marts.rpt_pricing_elasticity
