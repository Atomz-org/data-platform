-- source extract for view_cfo_revenue_summary (PII columns excluded by the MDL projection)
select month_start, total_revenue, total_expenses, gross_profit, net_profit, gross_margin_pct, net_profit_margin_pct, prev_month_revenue, revenue_mom_growth_pct
from main_marts.view_cfo_revenue_summary
