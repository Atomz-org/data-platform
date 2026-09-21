-- Grain: one commodity per market per price date.
-- Every market's landed price put back on the benchmark's own footing — USD per
-- the commodity's quote unit — so markets compare. Undo the FX at the rate the
-- sister used, then reprice market unit → quote unit with the group's factors.
-- The benchmark cancels out of the ratio by construction, which is the point:
-- what is left is what the market adds — duty, and the day the rate was fixed.
with landed as (
    select * from {{ ref('stg_sisters__landed_prices') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
)

select
    l.landed_price_id,
    l.market_code,
    l.commodity_id,
    l.price_date,
    l.price_basis,
    l.quote_unit,
    l.market_unit,
    l.currency_code,
    l.benchmark_price_usd,
    l.usd_fx_rate,
    l.fx_fixed_on,
    l.effective_duty_rate,
    l.is_import_prohibited,
    l.is_duty_rate_confirmed,
    l.landed_price_local,
    {{ reprice_per_unit('l.landed_price_local / nullif(l.usd_fx_rate, 0)',
                        'mu.base_units_per_unit', 'qu.base_units_per_unit') }}
                                                                            as landed_price_usd_per_quote_unit
from landed as l
inner join units as mu on mu.unit_code = l.market_unit
inner join units as qu on qu.unit_code = l.quote_unit
