-- source extract for rpt_daily_cash_flow (PII columns excluded by the MDL projection)
select cash_flow_date, location_id, location_name, daily_inflow, daily_refund_outflow, daily_expense_outflow, total_outflow, net_cash_flow, cumulative_net_cash_flow, rolling_7d_avg_net_cash_flow
from main_marts.rpt_daily_cash_flow
