-- source extract for kpi_employee_turnover_rate (PII columns excluded by the MDL projection)
select month_start, headcount, departures, turnover_rate_pct, annualized_turnover_pct
from main_marts.kpi_employee_turnover_rate
