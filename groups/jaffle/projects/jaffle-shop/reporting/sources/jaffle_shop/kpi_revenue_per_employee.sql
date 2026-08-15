-- source extract for kpi_revenue_per_employee (PII columns excluded by the MDL projection)
select month_start, location_id, monthly_revenue, avg_employees, revenue_per_employee
from main_marts.kpi_revenue_per_employee
