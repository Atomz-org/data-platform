-- source extract for hr_new_hire_retention (PII columns excluded by the MDL projection)
select hire_month, hired_count, retained_30_days, retained_60_days, retained_90_days, retention_rate_30d, retention_rate_60d, retention_rate_90d
from main_marts.hr_new_hire_retention
