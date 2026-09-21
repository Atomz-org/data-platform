-- Grain: one US exchange contract per price date.
-- The landed (import-parity) price expressed the way the contract trades: per
-- its quote basis and per lot. For a duty-free commodity this is the
-- benchmark's own contract value; for Section 232 metals it is what an imported
-- lot costs a US buyer over the benchmark. Computed from the benchmark, not
-- from a separate contract quote.
with landed as (
    select * from {{ ref('fct_landed_prices_daily') }}
    where landed_price_local is not null
),

lots as (
    select * from {{ ref('us_contract_lots') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
)

select
    lots.contract_code || ':' || cast(l.price_date as varchar)              as contract_value_id,
    lots.exchange,
    lots.contract_code,
    lots.contract_name,
    lots.commodity_id,
    l.price_date,
    l.price_basis,
    l.market_unit,
    l.effective_duty_rate,
    l.is_duty_rate_confirmed,
    lots.quote_size,
    lots.quote_unit,
    cast(round(
        lots.quote_size
        * {{ reprice_per_unit('l.landed_price_local', 'mu.base_units_per_unit', 'qu.base_units_per_unit') }}, 4
    ) as decimal(18, 4))                                                    as quote_equivalent_usd,
    lots.lot_size,
    lots.lot_unit,
    cast(round(
        lots.lot_size
        * {{ reprice_per_unit('l.landed_price_local', 'mu.base_units_per_unit', 'lu.base_units_per_unit') }}, 2
    ) as decimal(18, 2))                                                    as lot_value_usd
from lots
inner join landed as l on l.commodity_id = lots.commodity_id
inner join units as mu on mu.unit_code = l.market_unit
inner join units as qu on qu.unit_code = lots.quote_unit
inner join units as lu on lu.unit_code = lots.lot_unit
