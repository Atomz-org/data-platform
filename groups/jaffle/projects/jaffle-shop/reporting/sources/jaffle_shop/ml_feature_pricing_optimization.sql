-- source extract for ml_feature_pricing_optimization (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    current_unit_price,
    unit_cost,
    margin_pct,
    avg_daily_volume,
    estimated_price_elasticity
from main_marts.ml_feature_pricing_optimization
