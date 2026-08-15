-- source extract for alert_ar_overdue_90_days (PII columns excluded by the MDL projection)
select invoice_id, customer_id, amount_outstanding, due_date, days_overdue, alert_type, severity
from main_marts.alert_ar_overdue_90_days
