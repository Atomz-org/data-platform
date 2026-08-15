-- source extract for view_hr_headcount_dashboard (PII columns excluded by the MDL projection)
select department_id, department_name, position_title, location_id, total_headcount, active_count, inactive_count, active_pct
from main_marts.view_hr_headcount_dashboard
