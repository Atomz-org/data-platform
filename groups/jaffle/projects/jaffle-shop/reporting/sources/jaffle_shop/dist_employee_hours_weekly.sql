-- source extract for dist_employee_hours_weekly (PII columns excluded by the MDL projection)
select hours_bucket, week_count, avg_hours, mean_hours, p50, p75, p90
from main_marts.dist_employee_hours_weekly
