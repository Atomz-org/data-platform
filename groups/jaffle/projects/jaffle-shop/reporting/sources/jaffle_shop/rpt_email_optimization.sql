-- source extract for rpt_email_optimization (PII columns excluded by the MDL projection)
select hour_of_day, day_of_week, total_sent, total_opened, total_clicked, open_rate, click_rate, click_to_send_rate, day_name, time_period, open_rate_rank, click_rate_rank, engagement_score, overall_rank, send_time_quality
from main_marts.rpt_email_optimization
