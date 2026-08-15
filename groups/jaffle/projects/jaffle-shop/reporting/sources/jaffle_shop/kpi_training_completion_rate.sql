-- source extract for kpi_training_completion_rate (PII columns excluded by the MDL projection)
select completion_month, trained_employees, total_completions, total_employees, completion_rate_pct
from main_marts.kpi_training_completion_rate
