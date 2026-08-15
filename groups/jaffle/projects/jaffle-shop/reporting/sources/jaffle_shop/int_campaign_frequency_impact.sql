-- source extract for int_campaign_frequency_impact (PII columns excluded by the MDL projection)
select send_month, send_frequency_tier, avg_open_rate, avg_unsubscribe_rate, customer_count, avg_emails_sent, avg_click_rate, total_unsubscribes
from main_marts.int_campaign_frequency_impact
