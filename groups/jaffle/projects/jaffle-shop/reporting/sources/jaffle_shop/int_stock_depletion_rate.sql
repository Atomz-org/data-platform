-- source extract for int_stock_depletion_rate (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    location_id,
    current_quantity,
    daily_depletion_rate,
    estimated_days_of_stock
from main_marts.int_stock_depletion_rate
