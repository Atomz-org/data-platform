-- source extract for int_email_engagement_funnel (PII columns excluded by the MDL projection)
select campaign_id, open_rate, click_through_rate, unsubscribe_rate, email_subject, total_sent, total_opened, total_clicked, total_unsubscribed, total_bounced, unique_recipients, unique_openers, unique_clickers, click_to_send_rate, bounce_rate, first_event_date, last_event_date
from main_marts.int_email_engagement_funnel
