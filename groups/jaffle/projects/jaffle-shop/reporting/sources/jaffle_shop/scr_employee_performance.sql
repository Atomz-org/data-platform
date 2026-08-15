-- source extract for scr_employee_performance (PII columns excluded by the MDL projection)
select employee_id, performance_score, performance_tier, avg_orders_per_hour, total_hours_worked, days_worked, productivity_score, attendance_score, training_score, review_score_component, absenteeism_rate_pct, training_completion_pct, latest_review_score, review_trend_direction
from main_marts.scr_employee_performance
