-- Grain: one MCX contract per price date.
-- The landed price expressed the way an MCX contract is traded: per its quote
-- basis (₹ per 10 g for GOLDM, ₹ per kg for SILVER, ALUMINI, ZINCMINI) and per
-- lot (100 g, 30 kg, 1 MT, 5 MT). Equivalents computed from international
-- benchmarks — not MCX quotes; no MCX data is used.
with landed as (
    select * from {{ ref('fct_india_landed_prices_daily') }}
    where landed_price_inr is not null
),

lots as (
    select * from {{ ref('mcx_contract_lots') }}
),

units as (
    select * from {{ ref('units_of_measure') }}
)

select
    lots.contract_code || ':' || cast(l.price_date as varchar)              as lot_equivalent_id,
    'MCX'                                                                   as exchange,
    lots.contract_code,
    lots.contract_name,
    lots.commodity_id,
    l.price_date,
    l.price_basis,
    l.market_unit,
    l.is_duty_rate_confirmed,
    lots.quote_size,
    lots.quote_unit,
    cast(round(
        lots.quote_size
        * {{ reprice_per_unit('l.landed_price_inr', 'mu.base_units_per_unit', 'qu.base_units_per_unit') }}, 4
    ) as decimal(18, 4))                                                    as quote_equivalent_inr,
    lots.lot_size,
    lots.lot_unit,
    cast(round(
        lots.lot_size
        * {{ reprice_per_unit('l.landed_price_inr', 'mu.base_units_per_unit', 'lu.base_units_per_unit') }}, 2
    ) as decimal(18, 2))                                                    as lot_value_inr
from lots
inner join landed as l on l.commodity_id = lots.commodity_id
inner join units as mu on mu.unit_code = l.market_unit
inner join units as qu on qu.unit_code = lots.quote_unit
inner join units as lu on lu.unit_code = lots.lot_unit
