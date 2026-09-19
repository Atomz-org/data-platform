-- Grain: one MCX contract. The latest landed equivalent of every tracked MCX
-- contract, with how old its underlying benchmark is. Zinc has no free live
-- feed, so ZINC and ZINCMINI show the last indicative LME level until
-- `indicative_prices` is refreshed — `is_stale` says so.
with latest as (
    select *
    from {{ ref('fct_mcx_lot_equivalents_daily') }}
    qualify row_number() over (partition by contract_code order by price_date desc) = 1
)

select
    contract_code,
    exchange,
    contract_name,
    commodity_id,
    price_date,
    price_basis,
    is_duty_rate_confirmed,
    quote_size,
    quote_unit,
    quote_equivalent_inr,
    lot_size,
    lot_unit,
    lot_value_inr,
    {{ sf_datediff('day', 'price_date', 'current_date') }}                  as price_age_days,
    {{ sf_datediff('day', 'price_date', 'current_date') }} > 4              as is_stale
from latest
