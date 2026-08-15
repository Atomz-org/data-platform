-- source extract for rpt_employee_productivity_ranking (PII columns excluded by the MDL projection)
select employee_id, full_name, department_name, position_title, location_id, is_active, days_worked, total_hours_worked, total_orders_handled, avg_orders_per_hour, daily_avg_orders_per_hour, overall_productivity_rank, department_productivity_rank, performance_tier
from main_marts.rpt_employee_productivity_ranking
