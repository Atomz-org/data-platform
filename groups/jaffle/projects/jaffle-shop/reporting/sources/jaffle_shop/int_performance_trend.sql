-- source extract for int_performance_trend (PII columns excluded by the MDL projection)
select review_id, employee_id, review_date, review_period, overall_score, attendance_score, quality_score, teamwork_score, rolling_avg_score, previous_score, review_recency_rank, trend_direction
from main_marts.int_performance_trend
