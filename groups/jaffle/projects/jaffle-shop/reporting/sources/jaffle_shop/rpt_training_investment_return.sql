-- source extract for rpt_training_investment_return (PII columns excluded by the MDL projection)
select employee_id, training_roi_tier, full_name, total_required_courses, required_courses_completed, required_completion_pct, total_courses_completed, avg_training_score, performance_score, performance_tier, retention_status
from main_marts.rpt_training_investment_return
