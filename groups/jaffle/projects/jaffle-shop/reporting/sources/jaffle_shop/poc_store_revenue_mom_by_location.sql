-- source extract for poc_store_revenue_mom_by_location (PII columns excluded by the MDL projection)
select month_start, location_id, current_revenue, prior_month_revenue, mom_change_pct, fleet_avg_revenue, pct_of_fleet_avg
from main_marts.poc_store_revenue_mom_by_location
