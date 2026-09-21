-- source extract for int_daily_profit_by_store (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    location_id,
    profit_date,
    daily_profit,
    profit_margin_pct
from main_marts.int_daily_profit_by_store
