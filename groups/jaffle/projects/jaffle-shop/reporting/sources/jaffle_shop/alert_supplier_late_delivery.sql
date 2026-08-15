-- source extract for alert_supplier_late_delivery (PII columns excluded by the MDL projection)
select actual_arrival_at, supplier_id, purchase_order_id, actual_transit_days, days_late, alert_type, severity
from main_marts.alert_supplier_late_delivery
