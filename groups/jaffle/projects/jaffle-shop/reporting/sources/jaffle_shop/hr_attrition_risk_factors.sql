-- source extract for hr_attrition_risk_factors (PII columns excluded by the MDL projection)
select employee_id, full_name, department_name, position_title, tenure_months, is_active, termination_date, performance_score, avg_monthly_overtime, short_tenure_risk, high_overtime_risk, low_performance_risk, risk_factor_count, attrition_risk_level
from main_marts.hr_attrition_risk_factors
