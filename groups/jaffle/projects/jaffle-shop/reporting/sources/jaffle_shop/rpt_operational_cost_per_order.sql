-- source extract for rpt_operational_cost_per_order (PII columns excluded by the MDL projection)
select location_id, order_month, cost_per_order, monthly_orders, monthly_revenue, monthly_expenses, expense_revenue_ratio_pct
from main_marts.rpt_operational_cost_per_order
