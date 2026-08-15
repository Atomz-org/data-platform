-- source extract for poc_orders_wow (PII columns excluded by the MDL projection)
select week_start, location_id, current_orders, prior_week_orders, orders_change, orders_change_pct, current_aov, prior_aov
from main_marts.poc_orders_wow
