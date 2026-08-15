-- source extract for alert_gift_card_fraud_flag (PII columns excluded by the MDL projection)
select gift_card_id, initial_balance, latest_balance, total_spent, issued_date, alert_type, severity
from main_marts.alert_gift_card_fraud_flag
