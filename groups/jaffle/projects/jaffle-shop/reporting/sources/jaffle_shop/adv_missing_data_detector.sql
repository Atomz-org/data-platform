-- source extract for adv_missing_data_detector (PII columns excluded by the MDL projection)
select location_id, location_name, missing_date, last_order_date, next_order_date, days_since_last_order, days_until_next_order, severity
from main_marts.adv_missing_data_detector
