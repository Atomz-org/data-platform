-- source extract for alert_waste_spike (PII columns excluded by the MDL projection)
select waste_date, location_id, total_waste_cost, waste_14d_avg, pct_of_avg, alert_type, severity
from main_marts.alert_waste_spike
