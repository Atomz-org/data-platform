-- source extract for alert_stockout_risk (PII columns excluded by the MDL projection)
select product_id, location_id, current_quantity, daily_depletion_rate, estimated_days_of_stock, alert_type, severity
from main_marts.alert_stockout_risk
