-- source extract for sc_supplier_payment_history (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, total_orders, completed_orders, on_time_payments, on_time_payment_rate_pct, total_spend, avg_payment_cycle_days
from main_marts.sc_supplier_payment_history
