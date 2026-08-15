-- source extract for dim_warehouses (PII columns excluded by the MDL projection)
select warehouse_id, warehouse_name, address, city, state, warehouse_type, capacity_units, is_active, opened_at
from main_marts.dim_warehouses
