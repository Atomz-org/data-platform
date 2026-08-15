-- source extract for view_hr_turnover_report (PII columns excluded by the MDL projection)
select tenure_bucket, headcount, active_count, terminations, turnover_rate_pct, turnover_severity
from main_marts.view_hr_turnover_report
