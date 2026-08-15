-- source extract for alert_revenue_drop_weekly (PII columns excluded by the MDL projection)
select week_start, location_id, weekly_revenue, prior_week_revenue, wow_drop_pct, alert_type, severity
from main_marts.alert_revenue_drop_weekly
