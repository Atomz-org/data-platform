-- source extract for int_warehouse_throughput (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    warehouse_id,
    throughput_date,
    inbound_units,
    outbound_units,
    net_flow
from main_marts.int_warehouse_throughput
