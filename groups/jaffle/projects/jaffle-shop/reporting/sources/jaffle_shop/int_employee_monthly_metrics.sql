-- source extract for int_employee_monthly_metrics (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    employee_id,
    metric_month,
    total_hours,
    overtime_hours,
    overtime_pct,
    days_worked,
    attendance_rate_pct,
    orders_handled,
    avg_orders_per_hour
from main_marts.int_employee_monthly_metrics
