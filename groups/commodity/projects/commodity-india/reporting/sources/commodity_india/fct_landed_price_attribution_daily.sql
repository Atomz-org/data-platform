-- source extract for fct_landed_price_attribution_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    price_id,
    commodity_id,
    price_date,
    market_code,
    currency_code,
    landed_price_local,
    landed_change_20d_pct,
    benchmark_contribution_pct,
    fx_contribution_pct,
    duty_contribution_pct,
    fx_share_of_move,
    primary_driver,
    is_duty_rate_confirmed,
    is_latest,
    market_unit,
    is_import_prohibited,
    landed_price_local_20d_ago,
    benchmark_usd_per_market_unit,
    benchmark_20d_ago,
    usd_fx_rate,
    fx_20d_ago,
    effective_duty_rate,
    duty_rate_20d_ago
from main_marts.fct_landed_price_attribution_daily
