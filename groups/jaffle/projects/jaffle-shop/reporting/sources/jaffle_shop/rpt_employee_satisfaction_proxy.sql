-- source extract for rpt_employee_satisfaction_proxy (PII columns excluded by the MDL projection)
select employee_id, full_name, department_name, position_title, location_id, tenure_months, tenure_bucket, avg_weekly_overtime, latest_score, trend_direction, tenure_score, overtime_score, performance_trend_score, composite_satisfaction_score, satisfaction_tier
from main_marts.rpt_employee_satisfaction_proxy
