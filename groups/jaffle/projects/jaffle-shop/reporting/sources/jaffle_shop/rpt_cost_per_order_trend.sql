-- source extract for rpt_cost_per_order_trend (PII columns excluded by the MDL projection)
select location_id, location_name, report_month, order_count, total_order_revenue, total_expenses, cogs_amount, opex_amount, total_cost_per_order, cogs_per_order, opex_per_order, expense_to_revenue_ratio, prev_month_cost_per_order, cost_per_order_mom_change_pct, rolling_3m_avg_cost_per_order
from main_marts.rpt_cost_per_order_trend
