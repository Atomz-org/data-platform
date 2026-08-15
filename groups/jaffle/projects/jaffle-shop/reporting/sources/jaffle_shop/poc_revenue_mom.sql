-- source extract for poc_revenue_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_revenue, prior_month_revenue, current_orders, prior_month_orders, revenue_change, revenue_change_pct, performance_band
from main_marts.poc_revenue_mom
