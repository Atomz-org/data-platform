-- source extract for trend_email_open_rate (PII columns excluded by the MDL projection)
select event_date, sent_count, open_count, click_count, open_rate_pct, click_to_open_rate_pct, open_rate_7d_ma, open_rate_28d_ma
from main_marts.trend_email_open_rate
