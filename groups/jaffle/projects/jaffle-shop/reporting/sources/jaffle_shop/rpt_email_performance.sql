-- source extract for rpt_email_performance (PII columns excluded by the MDL projection)
select campaign_id, email_subject, total_sent, total_opened, total_clicked, total_unsubscribed, total_bounced, unique_recipients, unique_openers, unique_clickers, open_rate, click_through_rate, click_to_send_rate, unsubscribe_rate, bounce_rate, first_event_date, last_event_date, total_delivered, delivery_rate, open_rate_tier, ctr_tier
from main_marts.rpt_email_performance
