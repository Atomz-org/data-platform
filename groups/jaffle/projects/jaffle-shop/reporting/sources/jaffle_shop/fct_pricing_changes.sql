-- source extract for fct_pricing_changes (PII columns excluded by the MDL projection)
select pricing_history_id, product_id, product_name, product_type, old_price, new_price, price_change_amount, price_change_pct, price_change_direction, change_reason, price_changed_date, previous_change_date
from main_marts.fct_pricing_changes
