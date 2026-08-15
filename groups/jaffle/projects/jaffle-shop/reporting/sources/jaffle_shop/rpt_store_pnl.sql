-- source extract for rpt_store_pnl (PII columns excluded by the MDL projection)
select store_name, location_id, report_month, monthly_revenue, monthly_labor_cost, operating_expenses, marketing_spend, inventory_holding_cost, total_costs, net_profit, net_profit_margin_pct, labor_cost_ratio_pct, opex_ratio_pct, marketing_ratio_pct
from main_marts.rpt_store_pnl
