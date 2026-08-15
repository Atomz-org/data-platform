-- source extract for poc_delivery_count_mom (PII columns excluded by the MDL projection)
select delivery_month, current_deliveries, prior_month_deliveries, current_lead_time, prior_month_lead_time, on_time_pct, deliveries_mom_pct
from main_marts.poc_delivery_count_mom
