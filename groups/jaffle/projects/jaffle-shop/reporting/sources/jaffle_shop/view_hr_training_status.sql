-- source extract for view_hr_training_status (PII columns excluded by the MDL projection)
select department_name, total_employees, total_completed, total_non_compliant, completion_rate_pct, avg_score, compliance_status
from main_marts.view_hr_training_status
