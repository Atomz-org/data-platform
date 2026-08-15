-- source extract for rpt_training_completion (PII columns excluded by the MDL projection)
select department_name, total_employees, avg_required_completion_pct, fully_compliant_count, non_compliant_count, compliance_rate_pct, avg_training_score
from main_marts.rpt_training_completion
