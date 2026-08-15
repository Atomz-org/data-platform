-- source extract for rpt_360_workforce_dashboard (PII columns excluded by the MDL projection)
select location_id, active_employees, turnover_rate_pct, avg_tenure_days, terminated_employees, avg_daily_labor_cost
from main_marts.rpt_360_workforce_dashboard
