-- source extract for int_inventory_shrinkage (PII columns excluded by the MDL projection)
select product_id, location_id, shrinkage_quantity, shrinkage_pct, shrinkage_status, counted_quantity, expected_quantity, last_count_date
from main_marts.int_inventory_shrinkage
