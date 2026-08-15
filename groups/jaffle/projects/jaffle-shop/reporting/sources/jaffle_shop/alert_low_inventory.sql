-- source extract for alert_low_inventory (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, alert_type, severity
from main_marts.alert_low_inventory
