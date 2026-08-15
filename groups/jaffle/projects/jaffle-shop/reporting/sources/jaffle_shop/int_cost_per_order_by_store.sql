-- source extract for int_cost_per_order_by_store (PII columns excluded by the MDL projection)
select location_id, report_month, order_count, total_order_revenue, total_expenses, total_cost_per_order, cogs_per_order, opex_per_order, expense_to_revenue_ratio, cogs_amount, opex_amount
from main_marts.int_cost_per_order_by_store
