-- Grain: one commodity per market per price date. Every market's landed price
-- side by side: in her own currency per her unit as she reports it, and in USD
-- per the benchmark's quote unit so markets compare. The import-parity premium
-- is what landing in that market adds over the benchmark — the duty, and a
-- little FX timing where the fix was carried forward.
select
    landed_price_id,
    market_code,
    commodity_id,
    price_date,
    price_basis,
    quote_unit,
    market_unit,
    currency_code,
    benchmark_price_usd,
    usd_fx_rate,
    fx_fixed_on,
    effective_duty_rate,
    is_import_prohibited,
    is_duty_rate_confirmed,
    landed_price_local,
    cast(round(landed_price_usd_per_quote_unit, 6) as decimal(18, 6))       as landed_price_usd_per_quote_unit,
    round({{ sf_safe_divide('landed_price_usd_per_quote_unit - benchmark_price_usd', 'benchmark_price_usd') }}, 6)
                                                                            as import_parity_premium_pct
from {{ ref('int_landed_prices__usd_per_quote_unit') }}
