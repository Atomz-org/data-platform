-- source extract for hr_labor_productivity_trend (PII columns excluded by the MDL projection)
select month_start, active_employees, total_orders_handled, total_hours_worked, orders_per_labor_hour, orders_per_employee, prev_month_orders, mom_order_change_pct
from main_marts.hr_labor_productivity_trend
