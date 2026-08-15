-- source extract for sc_inventory_days_on_hand (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, daily_usage_rate, days_on_hand, inventory_health
from main_marts.sc_inventory_days_on_hand
