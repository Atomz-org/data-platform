-- source extract for ml_feature_employee_attrition (PII columns excluded by the MDL projection)
select employee_id, tenure_days, avg_orders_per_hour, avg_weekly_overtime, overtime_frequency_pct, training_completion_pct, attrition_label, department_name, position_title, is_management, pay_grade, location_id, tenure_months, tenure_bucket, avg_daily_hours, total_work_days, total_overtime_hours, courses_completed, avg_training_score
from main_marts.ml_feature_employee_attrition
