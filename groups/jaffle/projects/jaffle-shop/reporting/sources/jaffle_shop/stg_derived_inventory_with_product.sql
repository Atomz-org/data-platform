-- source extract for stg_derived_inventory_with_product (PII columns excluded by the MDL projection)
select movement_id, product_id, product_name, product_type, location_id, moved_at, movement_type, quantity
from main_marts.stg_derived_inventory_with_product
