-- source extract for rpt_workforce_diversity_metrics (PII columns excluded by the MDL projection)
select department_name, position_title, pay_grade, total_employees, active_employees, inactive_employees, avg_tenure_days, avg_tenure_months, pct_of_department, pct_of_organization, department_headcount, organization_headcount
from main_marts.rpt_workforce_diversity_metrics
