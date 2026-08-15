-- source extract for hr_labor_scheduling_efficiency (PII columns excluded by the MDL projection)
select location_id, shift_date, scheduled_employees, scheduled_shifts, demand_hours, actual_hours_worked, staffing_efficiency_pct, staffing_status
from main_marts.hr_labor_scheduling_efficiency
