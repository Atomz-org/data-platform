-- source extract for dq_stale_pricing (PII columns excluded by the MDL projection)
select product_id, days_since_last_change, staleness_level, product_name, current_price, last_price_change_date, total_price_changes
from main_marts.dq_stale_pricing
