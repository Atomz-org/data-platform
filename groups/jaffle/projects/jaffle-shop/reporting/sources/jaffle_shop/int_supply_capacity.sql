-- source extract for int_supply_capacity (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    supply_demand_gap,
    weeks_of_supply,
    stock_status
from main_marts.int_supply_capacity
