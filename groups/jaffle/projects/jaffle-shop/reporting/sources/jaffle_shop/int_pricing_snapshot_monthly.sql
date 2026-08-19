-- source extract for int_pricing_snapshot_monthly (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    month_start,
    product_id,
    price_at_month_end,
    last_change_reason,
    last_price_change_date
from main_marts.int_pricing_snapshot_monthly
