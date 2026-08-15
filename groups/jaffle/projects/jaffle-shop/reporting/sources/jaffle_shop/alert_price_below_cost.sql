-- source extract for alert_price_below_cost (PII columns excluded by the MDL projection)
select product_id, sale_date, selling_price, unit_cost, margin, alert_type, severity
from main_marts.alert_price_below_cost
