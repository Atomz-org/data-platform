-- Grain: one commodity per price date and basis. Every price in USD (major
-- units) per the commodity's quote unit — the single place cents become dollars.
-- Live futures and the manually maintained indicative levels share one shape
-- so every tracked commodity is priced through the same downstream path.
with futures as (
    select * from {{ ref('stg_yahoo_finance__futures_prices') }}
),

commodities as (
    select commodity_id, quote_unit from {{ ref('commodities') }}
),

indicative as (
    select * from {{ ref('indicative_prices') }}
)

select
    f.quote_id                                                        as price_id,
    f.commodity_id,
    cast(f.traded_at as date)                                         as price_date,
    'futures'                                                         as price_basis,
    c.quote_unit,
    {{ major_currency_code('f.currency_code') }}                      as currency_code,
    {{ to_major_currency('f.open_price', 'f.currency_code') }}        as open_price,
    {{ to_major_currency('f.high_price', 'f.currency_code') }}        as high_price,
    {{ to_major_currency('f.low_price', 'f.currency_code') }}         as low_price,
    {{ to_major_currency('f.close_price', 'f.currency_code') }}       as close_price,
    f.volume
from futures as f
inner join commodities as c on c.commodity_id = f.commodity_id

union all

select
    i.commodity_id || ':' || cast(i.as_of_date as varchar)            as price_id,
    i.commodity_id,
    i.as_of_date                                                      as price_date,
    'indicative'                                                      as price_basis,
    i.quote_unit,
    {{ major_currency_code('i.currency_code') }}                      as currency_code,
    cast(null as double)                                              as open_price,
    cast(null as double)                                              as high_price,
    cast(null as double)                                              as low_price,
    {{ to_major_currency('i.price', 'i.currency_code') }}             as close_price,
    cast(null as bigint)                                              as volume
from indicative as i
