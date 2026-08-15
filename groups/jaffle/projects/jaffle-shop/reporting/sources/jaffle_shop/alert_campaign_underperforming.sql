-- source extract for alert_campaign_underperforming (PII columns excluded by the MDL projection)
select campaign_id, campaign_name, total_spend, budget, budget_utilization, active_spend_days, alert_type, severity
from main_marts.alert_campaign_underperforming
