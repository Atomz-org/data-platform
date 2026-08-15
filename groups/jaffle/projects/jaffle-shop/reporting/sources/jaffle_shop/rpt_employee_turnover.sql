-- source extract for rpt_employee_turnover (PII columns excluded by the MDL projection)
select tenure_bucket, employee_count, active_count, terminated_count, turnover_rate_pct
from main_marts.rpt_employee_turnover
