-- source extract for int_employee_monthly_metrics (PII columns excluded by the MDL projection)
select employee_id, metric_month, total_hours, overtime_hours, overtime_pct, days_worked, attendance_rate_pct, orders_handled, avg_orders_per_hour, full_name, department_name, location_id, net_hours, total_break_minutes, total_shifts, no_show_shifts, late_arrivals
from main_marts.int_employee_monthly_metrics
