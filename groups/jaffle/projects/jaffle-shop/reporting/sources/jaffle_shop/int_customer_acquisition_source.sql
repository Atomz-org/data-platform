-- source extract for int_customer_acquisition_source (PII columns excluded by the MDL projection)
select customer_id, acquisition_source, campaign_name, customer_name, referrer_customer_id, campaign_id, campaign_channel, acquired_at
from main_marts.int_customer_acquisition_source
