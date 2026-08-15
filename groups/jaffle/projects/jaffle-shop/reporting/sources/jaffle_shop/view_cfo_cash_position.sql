-- source extract for view_cfo_cash_position (PII columns excluded by the MDL projection)
select cash_date, daily_inflow, daily_outflow, net_daily_cash_flow, cumulative_cash_position
from main_marts.view_cfo_cash_position
