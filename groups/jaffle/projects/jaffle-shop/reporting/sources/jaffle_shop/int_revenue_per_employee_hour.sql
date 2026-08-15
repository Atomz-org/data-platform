-- source extract for int_revenue_per_employee_hour (PII columns excluded by the MDL projection)
select store_id, work_date, revenue_per_labor_hour, revenue_per_employee, location_id, total_revenue, total_hours_worked, daily_labor_cost, employees_working, revenue_per_hour_7day_avg, store_avg_revenue_per_hour
from main_marts.int_revenue_per_employee_hour
