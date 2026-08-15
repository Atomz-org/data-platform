-- source extract for alert_revenue_drop_daily (PII columns excluded by the MDL projection)
select revenue_date, location_id, total_revenue, revenue_7d_avg, drop_pct, alert_type, severity
from main_marts.alert_revenue_drop_daily
