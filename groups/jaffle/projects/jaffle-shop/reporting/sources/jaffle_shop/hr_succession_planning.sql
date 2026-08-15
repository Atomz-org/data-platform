-- source extract for hr_succession_planning (PII columns excluded by the MDL projection)
select employee_id, full_name, position_title, department_name, tenure_months, performance_score, promotion_readiness, talent_category
from main_marts.hr_succession_planning
