-- source extract for stg_derived_waste_with_product (PII columns excluded by the MDL projection)
select waste_log_id, product_id, product_name, product_type, location_id, wasted_at, waste_reason, quantity_wasted, cost_of_waste
from main_marts.stg_derived_waste_with_product
