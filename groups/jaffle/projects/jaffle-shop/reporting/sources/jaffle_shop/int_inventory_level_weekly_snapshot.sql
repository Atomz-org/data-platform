-- source extract for int_inventory_level_weekly_snapshot (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    week_end_date,
    product_id,
    location_id,
    end_of_week_balance,
    weekly_inbound,
    weekly_outbound,
    movement_count
from main_marts.int_inventory_level_weekly_snapshot
