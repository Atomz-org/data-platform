-- source extract for poc_revenue_yoy (PII columns excluded by the MDL projection)
select month_start, location_id, current_revenue, prior_year_revenue, current_orders, prior_year_orders, revenue_yoy_change, revenue_yoy_change_pct
from main_marts.poc_revenue_yoy
