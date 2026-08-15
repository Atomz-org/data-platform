-- source extract for trend_revenue_per_employee (PII columns excluded by the MDL projection)
select work_date, location_id, revenue_per_employee, total_revenue, employee_count, rpe_7d_ma, rpe_28d_ma, productivity_band
from main_marts.trend_revenue_per_employee
