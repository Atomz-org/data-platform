-- source extract for int_price_elasticity_estimate (PII columns excluded by the MDL projection)
select product_id, price_changed_date, estimated_elasticity, old_price, new_price, price_change_pct, avg_daily_sales_before, avg_daily_sales_after, volume_change_pct
from main_marts.int_price_elasticity_estimate
