-- source extract for rpt_employee_development_tracker (PII columns excluded by the MDL projection)
select employee_id, career_stage, full_name, hire_date, tenure_days, total_required_courses, required_courses_completed, required_completion_pct, completion_status, avg_performance_score, review_count, latest_review_date
from main_marts.rpt_employee_development_tracker
