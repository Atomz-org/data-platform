-- source extract for alert_loyalty_churn_wave (PII columns excluded by the MDL projection)
select txn_month, active_members, prior_month_members, member_change_pct, alert_type, severity
from main_marts.alert_loyalty_churn_wave
