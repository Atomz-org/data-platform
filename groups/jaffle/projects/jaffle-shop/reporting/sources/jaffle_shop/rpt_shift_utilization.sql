-- source extract for rpt_shift_utilization (PII columns excluded by the MDL projection)
select location_id, location_name, report_month, total_shifts, total_scheduled_hours, total_actual_hours, timecard_hours_worked, timecard_net_hours, timecard_overtime_hours, no_show_count, late_arrival_count, unique_employees, utilization_pct, no_show_rate_pct, late_arrival_rate_pct
from main_marts.rpt_shift_utilization
