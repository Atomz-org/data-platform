-- source extract for fin_expense_per_transaction (PII columns excluded by the MDL projection)
select location_id, store_name, expense_month, total_expenses, total_orders, total_revenue, expense_per_transaction, expense_to_revenue_pct
from main_marts.fin_expense_per_transaction
