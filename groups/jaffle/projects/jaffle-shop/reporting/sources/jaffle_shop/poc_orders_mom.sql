-- source extract for poc_orders_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_orders, prior_month_orders, orders_mom_change, orders_mom_change_pct
from main_marts.poc_orders_mom
