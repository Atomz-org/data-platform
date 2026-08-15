-- source extract for int_overtime_by_department (PII columns excluded by the MDL projection)
select department_id, overtime_month, total_overtime_hours, employees_with_overtime, department_name, avg_overtime_hours_per_employee, max_overtime_hours
from main_marts.int_overtime_by_department
