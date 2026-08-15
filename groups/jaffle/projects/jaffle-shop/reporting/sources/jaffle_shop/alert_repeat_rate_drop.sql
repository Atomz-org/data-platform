-- source extract for alert_repeat_rate_drop (PII columns excluded by the MDL projection)
select month_start, repeat_rate, prior_month_rate, rate_change_pp, alert_type, severity
from main_marts.alert_repeat_rate_drop
