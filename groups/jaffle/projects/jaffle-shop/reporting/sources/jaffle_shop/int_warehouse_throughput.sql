-- source extract for int_warehouse_throughput (PII columns excluded by the MDL projection)
select warehouse_id, throughput_date, inbound_units, outbound_units, net_flow, warehouse_name, total_units_moved, distinct_products, movement_events
from main_marts.int_warehouse_throughput
