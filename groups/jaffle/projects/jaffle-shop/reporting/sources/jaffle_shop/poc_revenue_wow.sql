-- source extract for poc_revenue_wow (PII columns excluded by the MDL projection)
select week_start, location_id, current_revenue, prior_week_revenue, current_orders, prior_week_orders, revenue_change, revenue_change_pct, revenue_direction
from main_marts.poc_revenue_wow
