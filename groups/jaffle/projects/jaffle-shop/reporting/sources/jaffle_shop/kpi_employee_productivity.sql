-- source extract for kpi_employee_productivity (PII columns excluded by the MDL projection)
select metric_month, location_id, monthly_revenue, monthly_labor_hours, revenue_per_labor_hour, monthly_orders, orders_per_labor_hour
from main_marts.kpi_employee_productivity
