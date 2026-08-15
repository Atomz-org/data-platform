-- source extract for mkt_campaign_fatigue (PII columns excluded by the MDL projection)
select customer_id, touch_month, emails_received, emails_opened, open_rate, prev_month_open_rate, fatigue_status
from main_marts.mkt_campaign_fatigue
