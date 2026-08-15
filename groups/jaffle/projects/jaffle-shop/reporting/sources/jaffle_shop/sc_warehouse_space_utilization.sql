-- source extract for sc_warehouse_space_utilization (PII columns excluded by the MDL projection)
select warehouse_id, warehouse_name, warehouse_type, capacity_units, current_units_stored, utilization_pct, available_capacity, utilization_level
from main_marts.sc_warehouse_space_utilization
