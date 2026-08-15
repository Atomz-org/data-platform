-- source extract for int_labor_cost_daily (PII columns excluded by the MDL projection)
select location_id, work_date, total_hours, total_labor_cost, employee_count
from main_marts.int_labor_cost_daily
