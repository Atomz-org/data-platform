-- source extract for fct_landed_prices_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    landed_price_id,
    market_code,
    commodity_id,
    price_date,
    currency_code,
    benchmark_price_usd,
    usd_fx_rate,
    landed_price_local,
    landed_price_usd_per_quote_unit,
    import_parity_premium_pct,
    price_basis,
    quote_unit,
    market_unit,
    fx_fixed_on,
    effective_duty_rate,
    is_import_prohibited,
    is_duty_rate_confirmed
from main_marts.fct_landed_prices_daily
