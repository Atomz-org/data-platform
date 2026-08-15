-- source extract for rpt_warehouse_utilization (PII columns excluded by the MDL projection)
select warehouse_id, warehouse_name, city, state, warehouse_type, capacity_units, is_active, opened_at, distinct_products_stored, total_units_stored, utilization_rate, available_capacity, lifetime_inbound, lifetime_outbound, last_activity_at
from main_marts.rpt_warehouse_utilization
