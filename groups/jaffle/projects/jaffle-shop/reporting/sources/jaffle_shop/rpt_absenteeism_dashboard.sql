-- source extract for rpt_absenteeism_dashboard (PII columns excluded by the MDL projection)
select dimension, dimension_value, employee_count, total_shifts, total_absences, avg_absenteeism_rate_pct, high_absenteeism_employees
from main_marts.rpt_absenteeism_dashboard
