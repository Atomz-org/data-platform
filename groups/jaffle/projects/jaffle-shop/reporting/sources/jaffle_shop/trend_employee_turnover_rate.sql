-- source extract for trend_employee_turnover_rate (PII columns excluded by the MDL projection)
select month_start, headcount, new_hires, departures, turnover_rate_pct, turnover_3m_ma, turnover_12m_ma, turnover_severity
from main_marts.trend_employee_turnover_rate
