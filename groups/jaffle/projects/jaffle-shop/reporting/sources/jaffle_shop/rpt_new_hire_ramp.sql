-- source extract for rpt_new_hire_ramp (PII columns excluded by the MDL projection)
select ramp_phase, employee_count, total_work_days, avg_orders_per_hour, avg_daily_hours, avg_daily_orders, prev_phase_orders_per_hour, phase_over_phase_improvement_pct
from main_marts.rpt_new_hire_ramp
