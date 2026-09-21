-- Grain: one US exchange contract. The latest import-parity value of every
-- tracked contract per quote basis and per lot, with how old its benchmark is.
-- The LME metals and the other feedless commodities have no US contract here,
-- so this board is only ever live-feed contracts — stale means the feed.
with latest as (
    select *
    from {{ ref('fct_us_contract_values_daily') }}
    qualify row_number() over (partition by contract_code order by price_date desc) = 1
)

select
    contract_code,
    exchange,
    contract_name,
    commodity_id,
    price_date,
    price_basis,
    effective_duty_rate,
    is_duty_rate_confirmed,
    quote_size,
    quote_unit,
    quote_equivalent_usd,
    lot_size,
    lot_unit,
    lot_value_usd,
    {{ sf_datediff('day', 'price_date', 'current_date') }}                  as price_age_days,
    {{ sf_datediff('day', 'price_date', 'current_date') }} > 4              as is_stale
from latest
