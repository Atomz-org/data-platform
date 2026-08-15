-- source extract for inc_fct_email_events (PII columns excluded by the MDL projection)
select email_event_id, campaign_id, customer_id, email_event_type, event_at, event_date, event_month
from main_marts.inc_fct_email_events
