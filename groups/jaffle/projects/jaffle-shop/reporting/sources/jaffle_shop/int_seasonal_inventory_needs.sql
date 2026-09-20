-- source extract for int_seasonal_inventory_needs (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    demand_month,
    seasonal_index,
    season_classification
from main_marts.int_seasonal_inventory_needs
