-- source extract for alert_supplier_quality_issue (PII columns excluded by the MDL projection)
select last_receipt_date, supplier_id, purchase_order_id, quality_pass_rate_pct, rejection_reason, alert_type, severity
from main_marts.alert_supplier_quality_issue
