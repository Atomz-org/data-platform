-- source extract for int_email_send_time_analysis (PII columns excluded by the MDL projection)
select hour_of_day, day_of_week, open_rate, click_rate, total_sent, total_opened, total_clicked, click_to_send_rate
from main_marts.int_email_send_time_analysis
