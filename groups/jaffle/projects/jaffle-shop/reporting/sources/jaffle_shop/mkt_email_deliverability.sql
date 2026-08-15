-- source extract for mkt_email_deliverability (PII columns excluded by the MDL projection)
select campaign_id, total_sent, total_delivered, total_bounced, total_opened, total_clicked, total_unsubscribed, total_spam, delivery_rate_pct, bounce_rate_pct, spam_rate_pct, open_rate_pct, click_to_open_rate_pct
from main_marts.mkt_email_deliverability
