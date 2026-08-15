-- source extract for alert_email_bounce_spike (PII columns excluded by the MDL projection)
select event_date, sent, bounced, bounce_rate_pct, alert_type, severity
from main_marts.alert_email_bounce_spike
