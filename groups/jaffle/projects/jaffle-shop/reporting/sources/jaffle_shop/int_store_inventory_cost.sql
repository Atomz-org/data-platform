-- source extract for int_store_inventory_cost (PII columns excluded by the MDL projection)
select store_id, total_inventory_value, estimated_monthly_holding_cost, distinct_products_stocked, total_units_on_hand, avg_inventory_value_per_product, max_product_inventory_value, estimated_annual_holding_cost
from main_marts.int_store_inventory_cost
