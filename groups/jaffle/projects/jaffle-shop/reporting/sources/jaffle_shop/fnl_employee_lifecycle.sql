-- source extract for fnl_employee_lifecycle (PII columns excluded by the MDL projection)
select hire_quarter, department_name, stage_1_hired_count, stage_2_trained_count, stage_3_productive_count, training_completion_rate_pct, avg_days_to_productive, stage_4_reviewed_count, departed_count
from main_marts.fnl_employee_lifecycle
