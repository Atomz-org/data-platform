-- source extract for rpt_inventory_aging (PII columns excluded by the MDL projection)
select product_id, product_name, location_id, location_name, current_quantity, last_inbound_at, days_since_last_inbound, aging_bucket, aging_status
from main_marts.rpt_inventory_aging
