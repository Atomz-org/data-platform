-- source extract for int_email_unsubscribe_analysis (PII columns excluded by the MDL projection)
select campaign_id, unsubscribe_rate_pct, open_rate_pct, campaign_name, total_sent, total_unsubscribes, total_opens, total_clicks
from main_marts.int_email_unsubscribe_analysis
