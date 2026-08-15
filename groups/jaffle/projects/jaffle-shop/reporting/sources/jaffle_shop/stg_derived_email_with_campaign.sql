-- source extract for stg_derived_email_with_campaign (PII columns excluded by the MDL projection)
select email_event_id, campaign_id, campaign_name, campaign_channel, customer_id, email_event_type, event_date
from main_marts.stg_derived_email_with_campaign
