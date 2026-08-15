-- source extract for fct_email_events (PII columns excluded by the MDL projection)
select email_event_id, campaign_id, customer_id, email_event_type, email_subject, event_date, event_at, campaign_name, campaign_channel, campaign_status, campaign_start_date, campaign_end_date, is_sent, is_opened, is_clicked, is_unsubscribed, is_bounced
from main_marts.fct_email_events
