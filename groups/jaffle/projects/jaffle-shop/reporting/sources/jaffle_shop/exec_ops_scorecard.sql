-- source extract for exec_ops_scorecard (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    reporting_month,
    ops_health_score,
    avg_orders_per_labor_hour,
    waste_to_revenue_pct,
    avg_employee_performance_score
from main_marts.exec_ops_scorecard
