-- source extract for sc_inventory_accuracy (PII columns excluded by the MDL projection)
select product_id, location_id, system_quantity, physical_quantity, last_counted_at, variance_units, variance_pct, accuracy_status
from main_marts.sc_inventory_accuracy
