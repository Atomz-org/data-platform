-- source extract for alert_expense_spike (PII columns excluded by the MDL projection)
select expense_month, expense_category_id, total_expense_amount, avg_3m, spike_pct, alert_type, severity
from main_marts.alert_expense_spike
