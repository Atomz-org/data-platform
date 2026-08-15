-- source extract for poc_orders_yoy (PII columns excluded by the MDL projection)
select month_start, location_id, current_orders, prior_year_orders, orders_yoy_change, orders_yoy_change_pct
from main_marts.poc_orders_yoy
