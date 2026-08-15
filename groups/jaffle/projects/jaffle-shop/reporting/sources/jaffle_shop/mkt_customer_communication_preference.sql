-- source extract for mkt_customer_communication_preference (PII columns excluded by the MDL projection)
select customer_id, emails_sent, emails_opened, email_open_rate, coupons_redeemed, preferred_channel
from main_marts.mkt_customer_communication_preference
