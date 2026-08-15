-- source extract for view_hr_compliance_dashboard (PII columns excluded by the MDL projection)
select store_id, week_start, employees_with_violations, total_violations, compliance_status
from main_marts.view_hr_compliance_dashboard
