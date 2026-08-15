-- source extract for alert_high_waste_rate (PII columns excluded by the MDL projection)
select waste_date, location_id, total_waste_cost, total_revenue, waste_rate_pct, alert_type, severity
from main_marts.alert_high_waste_rate
