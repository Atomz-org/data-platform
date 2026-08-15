-- source extract for int_warehouse_cost_allocation (PII columns excluded by the MDL projection)
select warehouse_id, capacity_utilization_pct, total_inventory_value, warehouse_name, capacity_units, distinct_products, total_units_stored, avg_value_per_unit
from main_marts.int_warehouse_cost_allocation
