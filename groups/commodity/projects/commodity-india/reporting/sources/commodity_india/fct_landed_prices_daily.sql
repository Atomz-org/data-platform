-- source extract for fct_landed_prices_daily (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    price_id,
    market_code,
    commodity_id,
    price_date,
    market_unit,
    currency_code,
    benchmark_price_usd,
    usd_fx_rate,
    tariff_id,
    effective_duty_rate,
    is_duty_rate_confirmed,
    landed_price_local,
    duty_local,
    price_basis,
    quote_unit,
    benchmark_usd_per_market_unit,
    fx_fixed_on,
    duty_basis,
    is_import_prohibited,
    assessable_value_local,
    landed_price_change_local,
    landed_price_change_pct
from main_marts.fct_landed_prices_daily
