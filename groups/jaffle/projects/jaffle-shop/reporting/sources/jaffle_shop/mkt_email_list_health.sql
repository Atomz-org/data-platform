-- source extract for mkt_email_list_health (PII columns excluded by the MDL projection)
select customer_id, last_email_date, last_open_date, unsubscribe_date, total_opens, total_bounces, subscriber_status
from main_marts.mkt_email_list_health
