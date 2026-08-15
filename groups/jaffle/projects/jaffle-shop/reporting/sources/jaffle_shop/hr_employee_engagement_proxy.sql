-- source extract for hr_employee_engagement_proxy (PII columns excluded by the MDL projection)
select employee_id, full_name, department_name, tenure_months, absent_shifts, avg_monthly_overtime, engagement_score, engagement_category
from main_marts.hr_employee_engagement_proxy
