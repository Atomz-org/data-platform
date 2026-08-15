-- source extract for kpi_inventory_days_on_hand (PII columns excluded by the MDL projection)
select product_id, location_id, days_on_hand, doh_status
from main_marts.kpi_inventory_days_on_hand
