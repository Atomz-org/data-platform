-- source extract for exec_financial_summary_monthly (PII columns excluded by the MDL projection)
select month_start, total_revenue, gross_profit, gross_margin_pct, net_profit, net_profit_margin_pct, total_gross_revenue, total_orders, total_expenses, cogs, operating_expenses, operating_profit, operating_margin_pct, other_expenses, prev_month_revenue, mom_revenue_change
from main_marts.exec_financial_summary_monthly
