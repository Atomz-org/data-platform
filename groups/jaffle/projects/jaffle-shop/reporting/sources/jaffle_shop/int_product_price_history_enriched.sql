-- source extract for int_product_price_history_enriched (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    pricing_history_id,
    product_id,
    price,
    period_start,
    period_end,
    days_at_price,
    units_during_period,
    avg_daily_units_at_price,
    point_elasticity_estimate
from main_marts.int_product_price_history_enriched
